"""修复 Dream OS 上下文理解问题

根因：
1. Intent Detector 的上下文关键词太少，"有什么美食"不会被识别为需要上下文
2. System Prompt 没有强调结合对话历史理解意图
3. build_context 的对话历史太短（只取最近6条）
4. Intent 识别为 CHAT 时不带历史直接回复
"""

import os

# ── 修复1: Intent Detector — 增加上下文关键词 ──
filepath = os.environ.get("INTENT_FILE", "/dream-os/backend/app/core/intent_detector.py")
with open(filepath, "r") as f:
    content = f.read()

# 扩展上下文关联词
old_context = """# 上下文关联词 — 表明需要参考上一条消息
_CONTEXT_KEYWORDS = [
    r"^(?:再|还|也|又|那|另外|顺便|同样|继续|接着)",
    r"^(?:it|he|she|they|this|that|these|those)",
    r"^(?:他|她|它|他们|她们|它们|这个|那个|这些|那些)",
    r"^(?:看看|查查|查一下|问一下|对比|比较)",
]"""

new_context = """# 上下文关联词 — 表明需要参考上一条消息
_CONTEXT_KEYWORDS = [
    r"^(?:再|还|也|又|那|另外|顺便|同样|继续|接着)",
    r"^(?:it|he|she|they|this|that|these|those)",
    r"^(?:他|她|它|他们|她们|它们|这个|那个|这些|那些)",
    r"^(?:看看|查查|查一下|问一下|对比|比较)",
    # 新增：疑问短句也需要上下文（"有什么美食" → 结合前文知道是"汉中美食"）
    r"^(?:有什么|有哪些|介绍一下|推荐|推荐一下|说说|讲讲|告诉我|呢|吗|好不好|怎么样)",
    r"(?:美食|景点|特产|好玩|好吃|特色|攻略|注意|建议)",
    r"(?:那里|那里|那边|当地|本地|这边)",
]"""

content = content.replace(old_context, new_context)

# 修复2: detect_intent 函数 — 所有非 simple_chat 的意图都应该检查上下文
old_detect = """    # 检测是否需要上下文
    needs_context = False
    context_hint = ""
    for pattern in _CONTEXT_KEYWORDS:
        m = re.search(pattern, text_clean)
        if m:
            needs_context = True
            context_hint = f"开头'{m.group(0)}'表明可能引用前文"
            break"""

new_detect = """    # 检测是否需要上下文
    needs_context = False
    context_hint = ""
    for pattern in _CONTEXT_KEYWORDS:
        m = re.search(pattern, text_clean)
        if m:
            needs_context = True
            context_hint = f"'{m.group(0)}'表明可能引用前文"
            break

    # 如果消息很短（<15字）且是疑问句，几乎肯定需要上下文
    if not needs_context and len(text_clean) < 15 and (
        text_clean.endswith("？") or text_clean.endswith("?") or
        any(kw in text_clean for kw in ["有什么", "有哪些", "呢", "推荐", "说说", "介绍"])
    ):
        needs_context = True
        context_hint = "短疑问句通常需要结合前文理解" """

content = content.replace(old_detect, new_detect)

with open(filepath, "w") as f:
    f.write(content)

print("✅ intent_detector.py 修复完成（扩展上下文关键词）")


# ── 修复2: System Prompt — 强调上下文理解 ──
filepath2 = os.environ.get("PIPELINE_FILE", "/dream-os/backend/app/core/agent_pipeline.py")
with open(filepath2, "r") as f:
    content2 = f.read()

old_system = '''SYSTEM_PROMPT_DEFAULT = """你是 Dream OS，一个智能 AI 助手。

## 角色定位
你是一个能够理解上下文、主动推理的智能助手。你的核心能力是通过工具获取实时信息，然后给出准确的回答。

## 回答原则
1. 回答简洁、直接，不要冗余
2. 如果使用了工具获取数据，基于工具返回的真实数据回答
3. 不确定时明确说明，不要编造
4. 不要暴露工具调用细节'''

new_system = '''SYSTEM_PROMPT_DEFAULT = """你是 Dream OS，一个智能 AI 助手。

## 角色定位
你是一个能够理解上下文、主动推理的智能助手。你的核心能力是通过工具获取实时信息，然后给出准确的回答。

## ⚠️ 最重要的规则：上下文理解
你必须结合对话历史来理解用户的意图！
- 用户说"有什么美食" → 你必须从对话历史中找到上下文（如"汉中"），回答"汉中的美食"
- 用户说"推荐一下" → 你必须从对话历史中找到推荐什么
- 用户说"那边天气怎么样" → 你必须从对话历史中找到"那边"是哪里
- 用户说"呢"或"还有吗" → 必须继续前文的话题
绝对不要把用户的短句当作独立问题来回答！

## 回答原则
1. 回答简洁、直接，不要冗余
2. 如果使用了工具获取数据，基于工具返回的真实数据回答
3. 不确定时明确说明，不要编造
4. 不要暴露工具调用细节
5. 必须结合对话历史理解用户意图，不要孤立理解每句话'''

content2 = content2.replace(old_system, new_system)

# 修复3: build_context — 增加对话历史长度
old_history = """            history_parts = []
            for m in context_messages[-6:]:  # 最近3轮对话"""

new_history = """            history_parts = []
            for m in context_messages[-10:]:  # 最近5轮对话（增大上下文窗口）"""

content2 = content2.replace(old_history, new_history)

# 修复4: Intent CHAT 时也带上对话历史
old_chat_direct = """            # Step 7a: 无工具结果 — 直接使用完整上下文回复
        if not self._observation:
            response = await client.chat.completions.create(
                model=model,
                messages=context_messages,
                temperature=0.5,
                max_tokens=1024,
            )"""

new_chat_direct = """            # Step 7a: 无工具结果 — 直接使用完整上下文回复
        if not self._observation:
            # 即使是简单聊天，也确保完整上下文参与
            chat_messages = list(context_messages)
            # 如果意图需要上下文，在 system prompt 里强调
            if self._intent and self._intent.requires_context:
                chat_messages.insert(1, {
                    "role": "system",
                    "content": (
                        f"⚠️ 用户当前输入需要结合对话历史理解。{self._intent.context_hint}"
                        f"\\n请务必结合之前的对话内容来理解用户意图，不要孤立理解。"
                    ),
                })
            response = await client.chat.completions.create(
                model=model,
                messages=chat_messages,
                temperature=0.5,
                max_tokens=1024,
            )"""

content2 = content2.replace(old_chat_direct, new_chat_direct)

with open(filepath2, "w") as f:
    f.write(content2)

print("✅ agent_pipeline.py 修复完成（System Prompt + 上下文增强）")
