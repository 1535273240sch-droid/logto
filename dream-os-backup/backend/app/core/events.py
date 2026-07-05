"""Dream OS 事件系统 — 标准化的 Pipeline Step 事件协议

用于 AI 工作状态可视化的后端事件定义。
每个 Pipeline Step 对应一次 step_start + step_complete 事件对。
"""

import time
import json
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Optional


class StepStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


# ── 标准 Pipeline Step 定义 ──────────────────────────────

@dataclass
class StepDef:
    """Pipeline 步骤定义"""
    id: str          # 唯一标识
    label: str       # 显示文字（中文）
    emoji: str       # 步骤图标


# 完整的 Pipeline 步骤序列（按执行顺序）
PIPELINE_STEPS: list[StepDef] = [
    StepDef(id="context_builder",  label="正在理解问题...",     emoji="🧠"),
    StepDef(id="memory",           label="正在读取长期记忆...",  emoji="📚"),
    StepDef(id="context",          label="正在恢复历史上下文...", emoji="💬"),
    StepDef(id="intent_detector",  label="正在识别意图...",     emoji="🎯"),
    StepDef(id="planner",          label="正在制定计划...",     emoji="📋"),
    StepDef(id="router",           label="正在路由工具...",     emoji="🔗"),
    StepDef(id="executor",         label="正在调用工具...",     emoji="🔍"),
    StepDef(id="observation",      label="正在分析结果...",     emoji="📊"),
    StepDef(id="llm_final",        label="正在生成回答...",     emoji="✍️"),
]

STEP_MAP: dict[str, StepDef] = {s.id: s for s in PIPELINE_STEPS}


# ── 事件构建器 ──────────────────────────────

def make_step_start(step_id: str) -> str:
    """生成 step_start 事件

    前端收到后将该步骤标记为 running 状态，并显示 label 和 emoji。
    """
    s = STEP_MAP.get(step_id)
    payload = {
        "type": "step_start",
        "step": step_id,
        "label": s.label if s else step_id,
        "emoji": s.emoji if s else "",
        "status": "running",
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_step_complete(step_id: str, status: str = "success",
                       duration_ms: float = 0, error: str = "") -> str:
    """生成 step_complete 事件

    前端收到后将步骤标记为完成状态，显示耗时。
    """
    payload = {
        "type": "step_complete",
        "step": step_id,
        "status": status,
        "duration_ms": round(duration_ms, 1),
    }
    if error:
        payload["error"] = error[:200]
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_content(token: str) -> str:
    """生成 content 事件 — LLM 流式输出 token"""
    payload = {"type": "content", "content": token}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_done(intent: str = "", tools_used: list[str] = None,
              tool_count: int = 0, conversation_id: str = "") -> str:
    """生成 done 事件 — Pipeline 执行完成"""
    payload = {
        "type": "done",
        "intent": intent,
        "tools_used": tools_used or [],
        "tool_count": tool_count,
        "conversation_id": conversation_id,
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_error(msg: str) -> str:
    """生成 error 事件"""
    payload = {"type": "error", "content": str(msg)[:200]}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_tool_start(tool: str, step_id: str = "",
                    description: str = "", is_fallback: bool = False) -> str:
    """生成 tool_start 事件 — 单个工具开始执行"""
    payload = {
        "type": "tool_start",
        "tool": tool,
        "step": step_id,
        "description": description[:100],
        "status": "running",
    }
    if is_fallback:
        payload["is_fallback"] = True
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_tool_result(tool: str, status: str, duration_ms: float,
                     result_preview: str = "", error: str = "",
                     is_fallback: bool = False) -> str:
    """生成 tool_result 事件 — 工具执行结果"""
    payload = {
        "type": "tool_result",
        "tool": tool,
        "status": status,
        "duration_ms": round(duration_ms, 1),
    }
    if result_preview:
        payload["result_preview"] = result_preview[:300]
    if error:
        payload["error"] = error[:200]
    if is_fallback:
        payload["is_fallback"] = True
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_pipeline_start(conversation_id: str = "") -> str:
    """生成 pipeline_start 事件"""
    payload = {
        "type": "pipeline_start",
        "conversation_id": conversation_id,
        "steps": [s.id for s in PIPELINE_STEPS],
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_intent_event(intent_type: str, confidence: float,
                      entities: dict = None) -> str:
    """生成 intent 事件"""
    payload = {
        "type": "intent",
        "intent": intent_type,
        "confidence": confidence,
        "entities": entities or {},
    }
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_plan_event(plan_data: dict) -> str:
    """生成 plan 事件"""
    payload = {"type": "plan", "plan": plan_data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def make_tools_event(tools: list[str]) -> str:
    """生成 tools 事件 — 调度了哪些工具"""
    payload = {"type": "tools", "tools": tools}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


# ── 工具：计时器 ──────────────────────────────

@dataclass
class StepTimer:
    """步骤执行计时器"""
    step_times: dict[str, float] = field(default_factory=dict)

    def start(self, step_id: str):
        self.step_times[step_id] = time.time()

    def elapsed(self, step_id: str) -> float:
        t = self.step_times.get(step_id)
        if t is None:
            return 0.0
        return (time.time() - t) * 1000  # → ms

    def reset(self):
        self.step_times.clear()