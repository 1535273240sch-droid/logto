"""Dream OS V1.5 智能上下文记忆系统 — 低资源性能优化版

优化目标：
- 适配 2GB 内存服务器
- 所有耗时操作后台异步执行，不阻塞聊天
- 长期记忆提取仅在关键时机触发
- Token Budget 严格限制
- 内存缓存 + 自动过期

架构：
  System Prompt → 长期记忆(≤500) → 摘要(≤1000) → 最近消息(≤4000) → 用户输入
                                                          ↑ 后台异步任务
                                            ┌─────────────┴─────────────┐
                                            ▼                          ▼
                                     会话摘要生成                 长期记忆提取
                                     历史消息裁剪                 Token 统计更新
"""
import re
import json
import asyncio
import logging
import time
from typing import Optional, Callable
from sqlalchemy import select, delete, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.memory import Memory, Conversation, Message

logger = logging.getLogger("dream-os.memory")

# ──────────────────────────────────────────────
# Token 估算
# ──────────────────────────────────────────────
_AVG_CHARS_PER_TOKEN = 3.5


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / _AVG_CHARS_PER_TOKEN))


def truncate_to_token_limit(text: str, max_tokens: int) -> str:
    if not text or estimate_tokens(text) <= max_tokens:
        return text
    max_chars = int(max_tokens * _AVG_CHARS_PER_TOKEN)
    if len(text) <= max_chars:
        return text
    truncated = text[:max_chars]
    last_break = max(
        truncated.rfind("。"), truncated.rfind("."),
        truncated.rfind("！"), truncated.rfind("!"),
        truncated.rfind("？"), truncated.rfind("?"),
        truncated.rfind("\n"),
    )
    if last_break > max_chars * 0.5:
        truncated = truncated[: last_break + 1]
    return truncated + "\n\n[内容已截断...]"


# ──────────────────────────────────────────────
# Token Budget 常量
# ──────────────────────────────────────────────
TOKEN_LIMIT_LONG_TERM = 500      # 长期记忆 ≤ 500
TOKEN_LIMIT_SUMMARY = 1000       # 会话摘要 ≤ 1000
TOKEN_LIMIT_RECENT = 4000        # 最近消息 ≤ 4000
TOKEN_LIMIT_TOTAL = 8000         # 总 Prompt ≤ 80% 窗口(假设10k模型)

# ──────────────────────────────────────────────
# 长期记忆自动提取（仅关键词触发 + 间隔触发）
# ──────────────────────────────────────────────
# 高优先级关键词 — 用户明确要求记住
_HIGH_PRIORITY_PATTERNS = [
    (r"(?:以后一直|给我记住|记下来|请记住|记住(?:了|一下|这点|这个))[：:。，\s]*(.+)", 8),
    (r"记住[：:。，\s]*(.+)", 7),
]

# 低优先级关键词 — 用户信息/偏好
_MEDIUM_PATTERNS = [
    (r"(?:我[的正在]*(?:项目|任务|工作|开发))[：:。，\s]*(.+)", 7),
    (r"(?:项目(?:名字|名称))[：:。，\s]*(.+)", 8),
    (r"(?:我(?:叫|是|的名字))[：:。，\s]*(.+)", 7),
    (r"(?:我喜欢|我的爱好|我一直)", 6),
    (r"(?:以后都这样)", 6),
]


def extract_memories_from_text(text: str) -> list[tuple[str, int]]:
    """从用户消息中提取潜在的长期记忆

    性能优化：仅匹配关键词，不调用 AI 判断
    """
    if not text or len(text) < 5:
        return []
    extracted = []
    for pattern, importance in _HIGH_PRIORITY_PATTERNS:
        for m in re.finditer(pattern, text):
            val = m.group(1).strip() if m.lastindex and m.group(1) else m.group(0).strip()
            if val and len(val) > 3:
                extracted.append((val, importance))
    if not extracted:
        for pattern, importance in _MEDIUM_PATTERNS:
            for m in re.finditer(pattern, text):
                val = m.group(1).strip() if m.lastindex and m.group(1) else m.group(0).strip()
                if val and len(val) > 3:
                    extracted.append((val, importance))
    return extracted


# ──────────────────────────────────────────────
# 内存缓存（轻量级，自动过期）
# ──────────────────────────────────────────────
class MemoryCache:
    """内存缓存，用于活跃会话

    仅缓存最近消息和统计信息，不持久化。
    数据库是唯一持久化来源。
    支持按 category 分级 TTL。
    """

    # 分级 TTL 配置
    CATEGORY_TTL = {
        "task": 600,       # 多轮对话频繁引用
        "preference": 3600, # 用户偏好长期有效
        "fact": 120,        # 临时事实快速失效
        "default": 300,     # 默认 5 分钟
    }

    def __init__(self, ttl_seconds: int = 300):
        self._cache: dict[str, dict] = {}
        self._ttl = ttl_seconds

    def get(self, key: str) -> Optional[dict]:
        entry = self._cache.get(key)
        if entry:
            ttl = entry.get("_ttl", self._ttl)
            if time.time() - entry["_ts"] < ttl:
                return entry["data"]
        self._cache.pop(key, None)
        return None

    def set(self, key: str, data: dict, category: str = "default") -> None:
        ttl = self.CATEGORY_TTL.get(category, self._ttl)
        self._cache[key] = {"data": data, "_ts": time.time(), "_ttl": ttl}

    def invalidate(self, key: str) -> None:
        self._cache.pop(key, None)

    def clear_expired(self) -> int:
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v["_ts"] >= self._ttl]
        for k in expired:
            self._cache.pop(k, None)
        return len(expired)


# 全局缓存实例
_session_cache = MemoryCache(ttl_seconds=300)  # 5分钟自动过期


# ──────────────────────────────────────────────
# 上下文记忆管理器
# ──────────────────────────────────────────────

class ContextMemoryManager:
    """三层上下文记忆管理器 — 低资源优化版

    优化点：
    1. add_message 仅保存消息 + 轻量提取，不阻塞
    2. 摘要/裁剪/统计全部后台异步执行
    3. 长期记忆提取仅在消息数%10==0或匹配关键词时触发
    4. Prompt 组装有硬 Token 限制
    5. 内存缓存减少重复查询
    """

    AUTO_SUMMARIZE_THRESHOLD = 40      # 40条消息触发摘要
    RECENT_MESSAGE_KEEP = 20           # 摘要后保留最近20条
    EXTRACT_INTERVAL = 10              # 每10条检查一次长期记忆提取
    CACHE_KEY_PREFIX = "conv_"

    def __init__(self, session: AsyncSession, conversation_id: Optional[str] = None):
        self.session = session
        self._conversation_id = conversation_id
        self._user_id = "default"
        self._conversation: Optional[Conversation] = None
        self._message_count_cache: Optional[int] = None

    # ── 会话管理 ──────────────────────────────

    async def get_or_create_conversation(self, conversation_id: Optional[str] = None) -> Conversation:
        cid = conversation_id or self._conversation_id
        if cid:
            result = await self.session.execute(
                select(Conversation).where(Conversation.id == cid)
            )
            conv = result.scalar_one_or_none()
            if conv:
                self._conversation = conv
                self._conversation_id = conv.id
                self._message_count_cache = conv.message_count or 0
                return conv
        conv = Conversation(user_id=self._user_id, title="新对话", summary="")
        self.session.add(conv)
        await self.session.flush()
        self._conversation = conv
        self._conversation_id = conv.id
        self._message_count_cache = 0
        return conv

    async def get_conversation(self) -> Optional[Conversation]:
        if not self._conversation and self._conversation_id:
            result = await self.session.execute(
                select(Conversation).where(Conversation.id == self._conversation_id)
            )
            self._conversation = result.scalar_one_or_none()
        return self._conversation

    @property
    def conversation_id(self) -> Optional[str]:
        return self._conversation_id

    # ── 短期记忆：消息管理 ──────────────────────

    async def add_message(self, role: str, content: str) -> Message:
        """添加消息（只保存 + 计数更新，不阻塞）

        这是聊天的关键路径，只做最轻量的操作。
        """
        conv = await self.get_or_create_conversation()
        token_count = estimate_tokens(content)
        msg = Message(
            conversation_id=conv.id,
            role=role,
            content=content,
            token_count=token_count,
        )
        self.session.add(msg)
        if self._message_count_cache is not None:
            self._message_count_cache += 1
        conv.message_count = (conv.message_count or 0) + 1
        # 使缓存失效
        _session_cache.invalidate(f"{self.CACHE_KEY_PREFIX}{conv.id}")
        await self.session.flush()
        return msg

    async def get_recent_messages(self, limit: int = 20) -> list[Message]:
        """获取最近消息（走缓存）"""
        conv = await self.get_or_create_conversation()
        cache_key = f"{self.CACHE_KEY_PREFIX}{conv.id}_msgs_{limit}"
        cached = _session_cache.get(cache_key)
        if cached:
            return cached["msgs"]

        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(desc(Message.created_at))
            .limit(limit)
        )
        msgs = list(result.scalars().all())
        msgs.reverse()
        _session_cache.set(cache_key, {"msgs": msgs})
        return msgs

    async def get_recent_messages_for_prompt(self, max_tokens: int = TOKEN_LIMIT_RECENT) -> list[dict]:
        """获取最近消息用于 prompt 组装（硬 Token 限制）"""
        conv = await self.get_or_create_conversation()
        result = await self.session.execute(
            select(Message)
            .where(Message.conversation_id == conv.id)
            .order_by(Message.created_at)
        )
        all_messages = list(result.scalars().all())

        selected = []
        total_tokens = 0
        for msg in reversed(all_messages):
            msg_tokens = msg.token_count or estimate_tokens(msg.content)
            if total_tokens + msg_tokens > max_tokens:
                break
            total_tokens += msg_tokens
            selected.append(msg)

        selected.reverse()
        return [
            {"role": m.role, "content": m.content}
            for m in selected
        ]

    async def count_messages(self) -> int:
        """消息数（走缓存）"""
        if self._message_count_cache is not None:
            return self._message_count_cache
        conv = await self.get_or_create_conversation()
        result = await self.session.execute(
            select(func.count(Message.id))
            .where(Message.conversation_id == conv.id)
        )
        cnt = result.scalar() or 0
        self._message_count_cache = cnt
        return cnt

    # ── 会话摘要 ──────────────────────────────

    async def get_summary(self) -> str:
        conv = await self.get_or_create_conversation()
        return conv.summary or ""

    async def update_summary(self, summary: str) -> None:
        conv = await self.get_or_create_conversation()
        conv.summary = truncate_to_token_limit(summary, TOKEN_LIMIT_SUMMARY)
        conv.summary_token_count = estimate_tokens(conv.summary)
        await self.session.flush()

    async def needs_summarization(self) -> bool:
        """检查是否需要摘要（每40条或累计20条新消息）"""
        count = await self.count_messages()
        return count >= self.AUTO_SUMMARIZE_THRESHOLD

    async def summarize_and_cleanup_async(self, ai_summarize_func: Callable) -> None:
        """后台异步：生成摘要 + 裁剪历史消息

        这是后台任务，绝不阻塞聊天。
        """
        try:
            conv = await self.get_or_create_conversation()
            result = await self.session.execute(
                select(Message)
                .where(Message.conversation_id == conv.id)
                .order_by(Message.created_at)
            )
            all_messages = list(result.scalars().all())
            if len(all_messages) < self.AUTO_SUMMARIZE_THRESHOLD:
                return

            # 构建摘要文本（截断单条消息避免太大）
            summary_text = "\n".join([
                f"[{m.role}] {m.content[:300]}"
                for m in all_messages
            ])
            summary_text = truncate_to_token_limit(summary_text, 3000)

            # 调用 AI 生成摘要（带超时保护）
            try:
                new_summary = await asyncio.wait_for(
                    ai_summarize_func(summary_text), timeout=15
                )
            except asyncio.TimeoutError:
                logger.warning("AI summarization timed out, skipping")
                return
            except Exception as e:
                logger.error(f"AI summarization failed: {e}")
                return

            if not new_summary:
                return

            # 合并旧摘要
            old_summary = conv.summary or ""
            if old_summary:
                combined = f"【历史摘要】{old_summary}\n【新摘要】{new_summary}"
                new_summary = truncate_to_token_limit(combined, TOKEN_LIMIT_SUMMARY)

            conv.summary = new_summary
            conv.summary_token_count = estimate_tokens(new_summary)

            # 裁剪历史消息：只保留最近 RECENT_MESSAGE_KEEP 条
            if len(all_messages) > self.RECENT_MESSAGE_KEEP:
                keep_ids = [m.id for m in all_messages[-self.RECENT_MESSAGE_KEEP:]]
                await self.session.execute(
                    delete(Message).where(
                        Message.conversation_id == conv.id,
                        Message.id.notin_(keep_ids),
                    )
                )
                conv.message_count = self.RECENT_MESSAGE_KEEP
                self._message_count_cache = self.RECENT_MESSAGE_KEEP

            # 使缓存失效
            _session_cache.invalidate(f"{self.CACHE_KEY_PREFIX}{conv.id}")
            await self.session.flush()
            logger.info(f"会话 {conv.id[:8]} 摘要完成 + 消息裁剪")
        except Exception as e:
            logger.error(f"后台摘要任务失败: {e}")
            # 后台任务失败绝不向外传播

    # ── 长期记忆 ──────────────────────────────

    async def set_memory(self, key: str, value: str, category: str = "general",
                         importance: int = 5) -> None:
        result = await self.session.execute(
            select(Memory).where(Memory.key == key, Memory.user_id == self._user_id)
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.value = value
            existing.category = category
            existing.importance = importance
        else:
            self.session.add(Memory(
                key=key, user_id=self._user_id, value=value,
                category=category, importance=importance,
            ))
        await self.session.flush()

    async def get_memory(self, key: str) -> Optional[str]:
        result = await self.session.execute(
            select(Memory).where(Memory.key == key, Memory.user_id == self._user_id)
        )
        mem = result.scalar_one_or_none()
        return mem.value if mem else None

    async def get_all_memories(self) -> dict[str, dict]:
        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == self._user_id)
            .order_by(Memory.importance.desc(), Memory.category)
        )
        return {
            m.key: {"value": m.value, "category": m.category, "importance": m.importance}
            for m in result.scalars().all()
        }

    async def get_memories_for_prompt(self, max_tokens: int = TOKEN_LIMIT_LONG_TERM) -> str:
        """获取长期记忆文本用于 prompt（硬 Token 限制）"""
        conv = await self.get_or_create_conversation()
        cache_key = f"{self.CACHE_KEY_PREFIX}{conv.id}_memories"
        cached = _session_cache.get(cache_key)
        if cached:
            return cached["text"]

        result = await self.session.execute(
            select(Memory)
            .where(Memory.user_id == self._user_id)
            .order_by(Memory.importance.desc())
        )
        memories = result.scalars().all()

        lines = []
        total_tokens = estimate_tokens("【长期记忆】\n")
        for m in memories:
            line = f"- {m.key}: {m.value}"
            line_tokens = estimate_tokens(line)
            if total_tokens + line_tokens > max_tokens:
                break
            lines.append(line)
            total_tokens += line_tokens

        text = ("【长期记忆】\n" + "\n".join(lines)) if lines else ""
        _session_cache.set(cache_key, {"text": text})
        return text

    async def delete_memory(self, key: str) -> bool:
        result = await self.session.execute(
            select(Memory).where(Memory.key == key, Memory.user_id == self._user_id)
        )
        mem = result.scalar_one_or_none()
        if mem:
            await self.session.delete(mem)
            await self.session.flush()
            return True
        return False

    async def extract_memories_from_message(self, content: str) -> list[str]:
        """轻量同步提取（仅关键词匹配，不调 AI）

        优化策略：
        - 仅在消息数 % EXTRACT_INTERVAL == 0 或匹配关键词时执行
        - 使用正则匹配，不调用 AI
        """
        conv = await self.get_or_create_conversation()
        count = await self.count_messages()
        extracted = extract_memories_from_text(content)

        # 即使有关键词，也只在消息数%10或明确关键词时提取
        has_high_priority = any(imp >= 7 for _, imp in extracted)
        should_extract = (count % self.EXTRACT_INTERVAL == 0) or has_high_priority

        if not extracted or not should_extract:
            return []

        saved_keys = []
        for value, importance in extracted:
            key = f"auto_{hash(value) & 0xFFFFFF:06x}"
            existing = await self.get_memory(key)
            if existing:
                if importance > 5:
                    result = await self.session.execute(
                        select(Memory).where(Memory.key == key, Memory.user_id == self._user_id)
                    )
                    mem = result.scalar_one_or_none()
                    if mem:
                        mem.importance = max(mem.importance, importance)
                        await self.session.flush()
                continue
            await self.set_memory(key, value, category="auto_extracted", importance=importance)
            saved_keys.append(key)

        if saved_keys:
            logger.info(f"自动提取 {len(saved_keys)} 条长期记忆")
            _session_cache.invalidate(f"{self.CACHE_KEY_PREFIX}{conv.id}")

        return saved_keys

    # ── Prompt 组装 ──────────────────────────────

    async def build_context_prompt(self, system_prompt: str) -> list[dict]:
        """组装完整上下文 prompt（硬 Token 限制）

        组装顺序：
        System Prompt → 长期记忆(≤500) → 摘要(≤1000) → 最近消息(≤4000) → 用户输入
        总 Prompt ≤ TOKEN_LIMIT_TOTAL (8000)
        """
        messages = [{"role": "system", "content": system_prompt}]

        # 1. 长期记忆（有内存缓存）
        long_term = await self.get_memories_for_prompt(max_tokens=TOKEN_LIMIT_LONG_TERM)
        if long_term:
            messages.append({"role": "system", "content": long_term})

        # 2. 会话摘要
        summary = await self.get_summary()
        if summary:
            summary_text = truncate_to_token_limit(summary, TOKEN_LIMIT_SUMMARY)
            messages.append({"role": "system", "content": f"【对话历史摘要】\n{summary_text}"})

        # 3. 最近消息（硬 Token 限制）
        recent = await self.get_recent_messages_for_prompt(max_tokens=TOKEN_LIMIT_RECENT)
        messages.extend(recent)

        # 确保总长度不超过限制
        total = sum(estimate_tokens(m.get("content", "") or "") for m in messages)
        if total > TOKEN_LIMIT_TOTAL:
            logger.warning(f"Prompt 总长度 {total} 超过限制 {TOKEN_LIMIT_TOTAL}，正在裁剪")
            # 从摘要开始裁剪
            for m in messages:
                if m["role"] == "system" and "【对话历史摘要】" in (m.get("content", "") or ""):
                    content = m.get("content", "") or ""
                    ratio = TOKEN_LIMIT_TOTAL / total
                    new_max = int(estimate_tokens(content) * ratio * 0.8)
                    m["content"] = truncate_to_token_limit(content, max(new_max, 100))
                    break

        return messages

    # ── 后台异步维护 ──────────────────────────────

    async def schedule_async_maintenance(self, ai_summarize_func: Callable) -> None:
        """调度后台异步维护任务

        注意：这个函数会创建后台任务，不会阻塞调用者。
        调用者可以 safe fire-and-forget。
        """
        count = await self.count_messages()

        # 1. 摘要 + 裁剪（仅在消息数达到阈值时）
        if count >= self.AUTO_SUMMARIZE_THRESHOLD:
            task = asyncio.create_task(
                self.summarize_and_cleanup_async(ai_summarize_func)
            )
            task.add_done_callback(lambda t: None)  # 抑制未处理异常警告
            logger.info(f"已调度后台摘要任务 (消息数: {count})")

        # 2. 缓存清理
        if count % 20 == 0:
            expired = _session_cache.clear_expired()
            if expired:
                logger.debug(f"清理 {expired} 条缓存")

    # ── 旧版兼容 ──────────────────────────────

    async def get_recent(self, limit: int = 10) -> list:
        """兼容旧版 MemoryManager.get_recent"""
        result = await self.session.execute(
            select(Memory)
            .where(Memory.category == "task_memory", Memory.user_id == self._user_id)
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())

    async def add_task_memory(self, user_input: str, result_text: str) -> None:
        """兼容旧版 MemoryManager.add_task_memory"""
        import uuid
        content = f"User: {user_input}\nResult: {result_text[:500]}"
        key = f"task_{uuid.uuid4().hex[:12]}"
        self.session.add(Memory(
            key=key, user_id=self._user_id, value=content,
            category="task_memory", importance=3,
        ))
        await self._legacy_cleanup(max_records=200)
        await self.session.flush()

    async def _legacy_cleanup(self, max_records: int = 200) -> None:
        result = await self.session.execute(
            select(Memory.key)
            .where(Memory.category == "task_memory", Memory.user_id == self._user_id)
            .order_by(Memory.created_at.desc())
            .offset(max_records)
        )
        keys = [row[0] for row in result.fetchall()]
        if keys:
            await self.session.execute(delete(Memory).where(Memory.key.in_(keys)))