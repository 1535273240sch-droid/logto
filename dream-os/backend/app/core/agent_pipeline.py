"""Agent Pipeline — 完整 Agent 闭环

流程：
  Context Builder → Intent Detector → Planner → Router → Executor → Observation → LLM → Final

核心原则：
  1. 任一环节都不能跳过
  2. Tool 执行结果必须经过 Observation 层
  3. LLM 必须根据 Observation 生成最终回答
  4. 上下文参与所有环节
"""
import json
import asyncio
import logging
from typing import Optional, Callable

from ..models.task import Task
from ..db.session import get_db
from ..core.memory import ContextMemoryManager
from ..core.intent_detector import detect_intent, IntentType, IntentResult
from ..core.tool_registry import ToolRegistry, ToolExecutionRecord, ToolStatus
from ..core.planner import Planner, ExecutionPlan, PlanStep
from ..core.ai_provider import get_ai_client
from ..tools.image import ImageTool
from ..logger import TaskLogger

logger = logging.getLogger("dream-os.pipeline")

# ── 默认 Prompt ──────────────────────────────

SYSTEM_PROMPT_DEFAULT = """你叫「何惜 AI」，英文代号 Dream。

你是用户的 AI 智能伙伴，使命只有一个：帮用户把事情做好。

## 回复原则
1. 先给出答案，再解释
2. 数据查询结果用自然语言表达，不要直接输出 JSON
3. 简洁、逻辑清晰、不废话
4. 不要暴露工具调用细节

## 能力
- 实时数据查询（股票、黄金、天气、新闻）
- 服务器命令执行
- 文件读写
- 联网搜索"""

OBSERVATION_PROMPT = """你是一个数据观察器。你的职责是阅读工具返回的原始数据，整理为人类可理解的格式。

规则：
1. 提取关键信息，忽略无关字段
2. 用简洁的自然语言描述
3. 保留具体数值和时间
4. 不要添加原始数据中没有的信息
5. 如果数据为空或错误，直接说明

输出格式：纯文本，100字以内，不要 JSON。"""


# ── Observation 层 ──────────────────────────────

class Observation:
    """观察器 — 读取 Tool 返回数据，整理为 LLM 可理解的格式"""

    @staticmethod
    def format(record: ToolExecutionRecord) -> str:
        """格式化单条工具执行结果

        Args:
            record: 工具执行记录

        Returns:
            格式化后的观察文本
        """
        if record.status == ToolStatus.SUCCESS:
            result = record.result.strip() or "(无返回数据)"
            # 尝试格式化 JSON
            try:
                data = json.loads(result)
                result = json.dumps(data, ensure_ascii=False, indent=2)
            except (json.JSONDecodeError, ValueError):
                pass
            formatted = f"""
【工具: {record.tool_name}】
【状态: 成功 ({record.duration_ms}ms)】
【返回数据】
{result[:2000]}
"""
        elif record.status == ToolStatus.TIMEOUT:
            formatted = f"""
【工具: {record.tool_name}】
【状态: 超时 ({record.duration_ms}ms)】
【信息】工具执行超时，请重试或使用其他方式查询
"""
        elif record.status == ToolStatus.FAILED:
            formatted = f"""
【工具: {record.tool_name}】
【状态: 失败】
【错误】{record.error[:500]}
"""
        else:
            formatted = f"""
【工具: {record.tool_name}】
【状态: {record.status}】
【信息】工具未返回有效结果
"""

        return formatted

    @staticmethod
    def format_chain(records: list[ToolExecutionRecord]) -> str:
        """格式化多工具链结果"""
        parts = []
        for i, r in enumerate(records):
            parts.append(f"=== 步骤 {i+1}: {r.tool_name} ===")
            parts.append(Observation.format(r))
        return "\n".join(parts)


# ── Pipeline 日志 ──────────────────────────────


# ── 异步批量日志 ──────────────────────────────

class BatchLogger:
    """异步批量写入日志，减少数据库 IO 压力"""

    def __init__(self, db, flush_size: int = 10, flush_interval: float = 2.0):
        self.db = db
        self.flush_size = flush_size
        self.flush_interval = flush_interval
        self.buffer: list[dict] = []
        self._flush_task = None

    async def log(self, stage: str, data: dict):
        self.buffer.append({"stage": stage, "data": data})
        if len(self.buffer) >= self.flush_size:
            await self._flush()

    async def _flush(self):
        if not self.buffer:
            return
        batch = self.buffer[:]
        self.buffer = []
        # Bulk insert — 一次写入多行
        try:
            for entry in batch:
                logger.info(f"[Pipeline:{entry['stage']}] {json.dumps(entry['data'], ensure_ascii=False)[:200]}")
        except Exception as e:
            logger.warning(f"BatchLogger flush failed: {e}")

    def get_full_log(self) -> list[dict]:
        return self.buffer

class PipelineLogger:
    """Pipeline 全链路日志（批量写入版）"""

    def __init__(self, task_id: str, db_session):
        self.task_id = task_id
        self.db = db_session
        self.logs: list[dict] = []
        self._batch = BatchLogger(db_session)

    def log(self, stage: str, data: dict):
        entry = {
            "stage": stage,
            "data": data,
        }
        self.logs.append(entry)
        # 批量异步写入
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self._batch.log(stage, data))
            else:
                logger.info(f"[Pipeline:{stage}] {json.dumps(data, ensure_ascii=False)[:200]}")
        except RuntimeError:
            logger.info(f"[Pipeline:{stage}] {json.dumps(data, ensure_ascii=False)[:200]}")

    def get_full_log(self) -> list[dict]:
        return self.logs


# ── 完整 Agent Pipeline ──────────────────────────────

class AgentPipeline:
    """完整 Agent 闭环

    流程：
    1. Context Builder — 构建完整上下文
    2. Intent Detector — 识别意图
    3. Planner — 制定执行计划（含上下文）
    4. Router — 选择工具
    5. Executor — 执行工具
    6. Observation — 读取结果
    7. LLM Final — 生成最终回答
    8. Save — 保存消息 + 更新摘要 + 更新记忆
    """

    def __init__(self, db_session, conversation_id: Optional[str] = None):
        self.db = db_session
        self.memory = ContextMemoryManager(db_session, conversation_id)
        self.registry = ToolRegistry()
        self._register_tools()
        self.planner = Planner()
        self.pipeline_log: list[dict] = []

        # 运行时状态
        self._intent: Optional[IntentResult] = None
        self._plan: Optional[ExecutionPlan] = None
        self._tool_records: list[ToolExecutionRecord] = []
        self._observation: str = ""
        self._final_answer: str = ""

    def _log(self, stage: str, data: dict):
        self.pipeline_log.append({"stage": stage, "data": data})
        logger.info(f"[Pipeline:{stage}] {json.dumps(data, ensure_ascii=False)[:200]}")

    # ── Tool Registration ──────────────────────────────

    def _register_tools(self):
        """注册所有可用工具"""
        from ..tools.stock import StockTool
        from ..tools.weather import WeatherTool
        from ..tools.http import HttpTool
        self.registry.register("image_generate", ImageTool())
        self.registry.register("stock_query", StockTool())
        self.registry.register("weather_query", WeatherTool())
        self.registry.register("http_fetch", HttpTool())

    # ── Step 1: Context Builder ──────────────────────────────

    async def build_context(self, user_input: str) -> list[dict]:
        """构建完整上下文

        拼接：
        System Prompt + 长期记忆 + 摘要 + 最近消息 + 当前输入
        """
        await self.memory.get_or_create_conversation()
        messages = await self.memory.build_context_prompt(SYSTEM_PROMPT_DEFAULT)
        messages.append({"role": "user", "content": user_input})

        self._log("context_builder", {
            "message_count": len(messages),
            "conversation_id": self.memory.conversation_id,
        })
        return messages

    # ── Step 2: Intent Detector ──────────────────────────────

    async def detect_intent(self, user_input: str) -> IntentResult:
        """识别用户意图"""
        self._intent = detect_intent(user_input)
        self._log("intent_detector", {
            "intent": self._intent.intent_type,
            "confidence": self._intent.confidence,
            "requires_context": self._intent.requires_context,
            "entities": self._intent.entities,
        })
        return self._intent

    # ── Step 3: Planner ──────────────────────────────

    async def plan(self, user_input: str, context_messages: list[dict]) -> ExecutionPlan:
        """制定执行计划（含完整上下文）

        Context 必须参与 Planner 决策：
        - 用户说"再看看阿里" → 从历史知道"阿里"是股票
        - 用户说"再分析下" → 从历史知道要分析什么
        """
        client, model = await get_ai_client(tier="deep")

        # 如果意图是 CHAT，直接返回空计划
        if self._intent and self._intent.intent_type == IntentType.CHAT:
            self._plan = ExecutionPlan(
                task_summary=user_input[:60],
                steps=[], estimated_tools=[], risk_level="safe",
            )
            self._log("planner", {"steps": 0, "reason": "chat_intent"})
            return self._plan

        # 获取完整对话历史作为 Planner 上下文
        try:
            # 从 context_messages 提取最近对话
            history_parts = []
            for m in context_messages[-10:]:  # 最近5轮对话（增大上下文窗口）
                if m["role"] in ("user", "assistant"):
                    role_label = "用户" if m["role"] == "user" else "AI"
                    history_parts.append(f"[{role_label}] {m['content'][:200]}")
            history_text = "\n".join(history_parts)

            # 上下文提示：Intent Detector 已经识别了是否需要上下文
            context_hint = ""
            if self._intent and self._intent.requires_context:
                context_hint = (
                    f"\n【上下文提示】用户输入'{self._intent.context_hint}'，"
                    f"表明引用了前文。请结合对话历史理解完整意图。"
                    f"\n例如：'再看看阿里' → 用户想查询阿里巴巴股票"
                    f"\n例如：'再分析下' → 用户想继续之前话题的分析"
                )

            enhanced_input = user_input
            if history_text:
                enhanced_input = (
                    f"【最近对话历史】\n{history_text}\n\n"
                    f"【当前用户输入】{user_input}"
                    f"{context_hint}"
                )

            self._plan = await self.planner.plan(enhanced_input, client, model)

        except Exception as e:
            logger.warning(f"Planner failed: {e}")
            self._plan = ExecutionPlan(
                task_summary=user_input[:60],
                steps=[], estimated_tools=[], risk_level="safe",
            )

        self._log("planner", {
            "steps": len(self._plan.steps),
            "tools": self._plan.estimated_tools,
            "summary": self._plan.task_summary[:100],
            "context_used": bool(history_text),
        })
        return self._plan

    # ── Step 4: Router ──────────────────────────────

    def route(self) -> list[str]:
        """路由：Intent → 工具列表"""
        if not self._intent:
            return []

        # 如果 Planner 已指定工具，优先使用
        if self._plan and self._plan.estimated_tools:
            tools = []
            for t in self._plan.estimated_tools:
                if self.registry.get(t):
                    tools.append(t)
            if tools:
                self._log("router", {"tools": tools, "source": "planner"})
                return tools

        # 否则按 Intent 路由
        tools = self.registry.route(self._intent.intent_type)
        self._log("router", {"tools": tools, "source": "intent"})
        return tools

    # ── Step 5: Executor ──────────────────────────────

    async def execute(self, plan: ExecutionPlan, tools: list[str]) -> list[ToolExecutionRecord]:
        """执行计划和工具

        Args:
            plan: 执行计划
            tools: 可用工具列表

        Returns:
            工具执行记录列表
        """
        self._tool_records = []

        if not plan.steps:
            self._log("executor", {"steps": 0, "reason": "no_plan_steps"})
            return []

        # 按步骤执行
        for step in plan.steps:
            tool_name = step.tool
            if not tool_name:
                # 尝试从 action 推断工具
                tool_name = self.registry.get_tool_for_command(step.action)
                if not tool_name:
                    continue

            # 构造命令
            command = step.action
            if step.tool_args and "command" in step.tool_args:
                command = step.tool_args["command"]

            # 执行
            record = await self.registry.execute(tool_name, command, timeout=30)
            record.intent = self._intent.intent_type if self._intent else ""
            self._tool_records.append(record)

            # 如果失败且还有重试次数，尝试备用工具
            if record.status == ToolStatus.FAILED or record.status == ToolStatus.TIMEOUT:
                fallback_tools = [t for t in tools if t != tool_name]
                if fallback_tools:
                    fallback = fallback_tools[0]
                    logger.info(f"Step failed, trying fallback tool: {fallback}")
                    fallback_record = await self.registry.execute(fallback, command, timeout=30)
                    fallback_record.intent = self._intent.intent_type if self._intent else ""
                    self._tool_records.append(fallback_record)

        self._log("executor", {
            "executed": len(self._tool_records),
            "success": sum(1 for r in self._tool_records if r.status == ToolStatus.SUCCESS),
            "failed": sum(1 for r in self._tool_records if r.status == ToolStatus.FAILED),
        })
        return self._tool_records

    async def execute_tool(self, tool_name: str, command: str) -> ToolExecutionRecord:
        """直接执行指定工具（绕过 Planner，用于强制路由）

        Args:
            tool_name: 工具名称（如 "image_generate"）
            command: 执行命令

        Returns:
            工具执行记录
        """
        record = await self.registry.execute(tool_name, command, timeout=30)
        if record:
            record.intent = self._intent.intent_type if self._intent else ""
            self._tool_records.append(record)
        return record

    # ── Step 6: Observation ──────────────────────────────

    async def observe(self) -> str:
        """观察器：读取工具结果，整理为 LLM 可理解的格式"""
        if not self._tool_records:
            self._observation = ""
            self._log("observation", {"has_data": False})
            return ""

        self._observation = Observation.format_chain(self._tool_records)
        self._log("observation", {
            "has_data": True,
            "length": len(self._observation),
            "records": len(self._tool_records),
        })
        return self._observation

    # ── Step 7: LLM Final ──────────────────────────────

    async def llm_final(self, context_messages: list[dict], user_input: str) -> str:
        """LLM 根据【完整上下文 + Observation】生成最终回答

        这是必须的步骤：
        1. LLM 必须读取 Observation 结果，不能直接输出 JSON
        2. LLM 必须参考完整上下文（System Prompt + 长期记忆 + 摘要 + 最近聊天）
        3. 没有 Observation，Agent 不允许结束
        """
        client, model = await get_ai_client(tier="deep")

        # Step 7a: 无工具结果 — 直接使用完整上下文回复
        if not self._observation:
            response = await client.chat.completions.create(
                model=model,
                messages=context_messages,
                temperature=0.5,
                max_tokens=1024,
            )
            self._final_answer = response.choices[0].message.content or ""
            self._log("llm_final", {"mode": "direct", "length": len(self._final_answer)})
            return self._final_answer

        # Step 7b: 有 Observation — 注入到完整上下文中，LLM 读取后生成自然语言
        try:
            # 保留完整上下文（System Prompt + 长期记忆 + 摘要 + 最近聊天）
            llm_messages = list(context_messages)

            # 注入 Observation 数据（替换最后一条 user message 或追加）
            llm_messages.append({
                "role": "system",
                "content": (
                    f"{OBSERVATION_PROMPT}\n\n"
                    f"以下是从工具获取的原始数据，请根据这些数据回答用户的问题。\n"
                    f"不要直接输出 JSON，用自然语言。\n"
                    f"如果数据包含数值，请保留具体数值。\n\n"
                    f"{self._observation}"
                ),
            })

            # 确保末尾有用户输入
            if not any(m.get("role") == "user" and m.get("content", "").strip() == user_input.strip()
                       for m in llm_messages):
                llm_messages.append({"role": "user", "content": user_input})

            response = await client.chat.completions.create(
                model=model,
                messages=llm_messages,
                temperature=0.4,
                max_tokens=1024,
            )
            self._final_answer = response.choices[0].message.content or ""
        except Exception as e:
            logger.error(f"LLM final failed: {e}")
            # Fallback: 直接返回 Observation 整理后的数据
            self._final_answer = self._observation[:500]

        self._log("llm_final", {
            "mode": "with_observation",
            "length": len(self._final_answer),
            "context_messages": len(context_messages),
        })
        return self._final_answer

    # ── Step 8: Save ──────────────────────────────

    async def save(self, user_input: str, final_answer: str):
        """保存消息 + 更新摘要 + 更新记忆"""
        # 保存消息
        await self.memory.add_message("user", user_input)
        await self.memory.add_message("assistant", final_answer)

        # 提取长期记忆
        await self.memory.extract_memories_from_message(user_input)

        # 兼容旧版任务记忆
        await self.memory.add_task_memory(user_input, final_answer)

        # 后台调度摘要（不阻塞）
        try:
            async def _summarize(text):
                c, m = await get_ai_client(tier="deep")
                r = await c.chat.completions.create(
                    model=m,
                    messages=[
                        {"role": "system", "content": "高效对话摘要助手，总结这段对话。"},
                        {"role": "user", "content": f"总结:\n\n{text[:4000]}"},
                    ],
                    temperature=0.3, max_tokens=300,
                )
                return r.choices[0].message.content or ""
            await self.memory.schedule_async_maintenance(_summarize)
        except Exception as e:
            logger.warning(f"Background maintenance skipped: {e}")

        self._log("save", {
            "messages": 2,
            "conversation_id": self.memory.conversation_id,
        })

    # ── Full Pipeline Run ──────────────────────────────

    async def run(self, user_input: str) -> dict:
        """完整运行一次 Agent Pipeline

        Returns:
            {
                "answer": str,
                "intent": str,
                "plan": dict,
                "tool_records": list,
                "observation": str,
                "pipeline_log": list,
                "conversation_id": str,
            }
        """
        try:
            # Step 1+2: Context Builder + Intent Detector (并行执行)
            context_task = self.build_context(user_input)
            intent_task = self.detect_intent(user_input)
            context_messages, intent = await asyncio.gather(context_task, intent_task)

            # Step 3: Planner
            plan = await self.plan(user_input, context_messages)

            # 如果是聊天或空计划，直接 LLM 回答
            if not plan.steps:
                self._log("pipeline", {"mode": "direct_chat"})
                final_answer = await self.llm_final(context_messages, user_input)
                await self.save(user_input, final_answer)
                return self._result(final_answer, intent, plan, [])

            # Step 4: Router
            tools = self.route()

            # Step 5: Executor
            records = await self.execute(plan, tools)

            # Step 6: Observation
            observation = await self.observe()

            # Step 7: LLM Final
            final_answer = await self.llm_final(context_messages, user_input)

            # Step 8: Save (fire-and-forget，不阻塞响应)
            asyncio.create_task(self.save(user_input, final_answer))

            return self._result(final_answer, intent, plan, records)

        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            # 失败时至少返回一个回答
            fallback = f"抱歉，处理过程中出现错误: {str(e)[:200]}"
            return {
                "answer": fallback,
                "intent": str(self._intent) if self._intent else "unknown",
                "plan": self._plan.to_frontend() if self._plan else {},
                "tool_records": [],
                "observation": self._observation,
                "pipeline_log": self.pipeline_log,
                "conversation_id": self.memory.conversation_id or "",
                "error": str(e),
            }

    def _result(self, answer: str, intent: IntentResult,
                plan: ExecutionPlan, records: list[ToolExecutionRecord]) -> dict:
        return {
            "answer": answer,
            "intent": intent.intent_type if intent else "",
            "intent_confidence": intent.confidence if intent else 0,
            "entities": intent.entities if intent else {},
            "plan": plan.to_frontend() if plan else {},
            "tool_records": [
                {
                    "tool": r.tool_name,
                    "status": r.status,
                    "duration_ms": r.duration_ms,
                    "result_preview": r.result[:200],
                    "error": r.error[:200],
                }
                for r in records
            ],
            "observation": self._observation,
            "pipeline_log": self.pipeline_log,
            "conversation_id": self.memory.conversation_id or "",
        }