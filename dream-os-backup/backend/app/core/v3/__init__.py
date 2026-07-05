"""Dream OS V3 — 自主软件工程师 (Autonomous Software Engineer)

多 Agent 协作编排系统，让 AI 能自主完成完整软件开发项目。

核心组件:
  - BaseAgent: Agent 基类，内置 ReAct 循环 + function calling
  - SharedBlackboard: 项目级共享上下文 (Agent 间通信)
  - Workspace: 物理工作空间管理 (目录 + Git)
  - Orchestrator: 状态机驱动的多 Agent 编排
  - SSEv2: 增强事件协议 (支持 agent 维度)
  - AutoLoop: 自主循环引擎 (失败自动修复)

8 个专业 Agent:
  Planner → Architect → Coder → Executor → Reviewer → Tester → Deployer → Reporter
"""

from .blackboard import SharedBlackboard
from .base_agent import BaseAgent, AgentResult
from .workspace import Workspace
from .sse_v2 import SSEv2
from .orchestrator import Orchestrator, OrchestratorState
from .auto_loop import AutoLoop

__all__ = [
    "SharedBlackboard",
    "BaseAgent",
    "AgentResult",
    "Workspace",
    "SSEv2",
    "Orchestrator",
    "OrchestratorState",
    "AutoLoop",
]
