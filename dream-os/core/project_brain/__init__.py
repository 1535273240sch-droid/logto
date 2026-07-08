"""Project Brain - Dream OS 项目状态内核

Project Brain 不属于 Agent。
不负责聊天。
不负责开发。
属于 Dream OS 系统内核。
永久后台运行。

职责:
- 记录整个项目实时状态
- 所有 Agent 开始工作前必须读取
- 所有 Agent 完成工作后必须更新
- 所有 Agent 共用同一份项目状态
- 禁止重复分析、重复审核、重复规划

优先级: SYSTEM（最高优先级）
状态: Always Running
"""
from .brain import ProjectBrain
from .state import ProjectState
from .log import WorkLog

__all__ = ["ProjectBrain", "ProjectState", "WorkLog"]