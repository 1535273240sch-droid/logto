"""Agent 基类"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class ExecutionResult:
    step_id: int
    step_name: str
    agent: str
    tool: str
    command: str
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    duration_ms: int = 0


class BaseAgent(ABC):
    """所有 Agent 的基类"""

    name: str = "base"
    description: str = "Base agent"
    tools: list[str] = []

    @abstractmethod
    async def execute(self, step: dict, tool_manager) -> ExecutionResult:
        """执行一个任务步骤"""
        ...

    def to_info(self) -> dict:
        return {
            "name": self.name,
            "description": self.description,
            "tools": self.tools,
        }
