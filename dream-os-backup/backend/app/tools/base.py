"""Tool 基类 & Tool Manager - 统一工具注册与调用"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolResult:
    success: bool
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    extra: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """所有工具的基类"""

    name: str = "base"
    description: str = "Base tool"

    @abstractmethod
    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行工具命令"""
        ...

    def to_schema(self) -> dict:
        """返回 OpenAI function calling schema"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": f"要执行的 {self.name} 命令",
                        }
                    },
                    "required": ["command"],
                },
            },
        }


class ToolManager:
    """统一管理所有工具，Agent 只能通过 ToolManager 调用工具"""

    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict]:
        return [
            {"name": t.name, "description": t.description}
            for t in self._tools.values()
        ]

    def list_schemas(self) -> list[dict]:
        return [t.to_schema() for t in self._tools.values()]

    def list_names(self) -> list[str]:
        return list(self._tools.keys())
