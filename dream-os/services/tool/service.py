"""Tool Service - 工具注册和执行服务"""
from typing import Optional
from ..base import BaseService


class ToolService(BaseService):
    name = "tool"
    version = "1.0.0"

    async def initialize(self):
        try:
            from dream_os.backend.app.core.tool_registry import ToolRegistry
            from dream_os.backend.app.core.tool_center import ToolCenter
            self._tool_available = True
        except ImportError:
            self._tool_available = False
        return self

    async def execute_tool(self, tool_name, command, timeout=30):
        try:
            from dream_os.backend.app.core.tool_center import get_tool_center
            center = get_tool_center()
            result = await center.execute(tool_name, command, timeout=timeout)
            return {
                "tool": tool_name,
                "status": result.status,
                "result": result.result[:2000] if result.result else "",
                "error": result.error[:500] if result.error else "",
                "duration_ms": result.duration_ms,
            }
        except Exception as e:
            return {"tool": tool_name, "status": "error", "error": str(e)[:200]}

    async def list_tools(self):
        try:
            from dream_os.backend.app.core.tool_center import get_tool_center
            center = get_tool_center()
            return center.list_configs()
        except Exception:
            return []

    async def get_tool_status(self, tool_name):
        try:
            from dream_os.backend.app.core.tool_center import get_tool_center
            center = get_tool_center()
            cfg = center.get_config(tool_name)
            if cfg:
                return {"tool": tool_name, "status": "enabled" if cfg.enabled else "disabled",
                        "timeout": cfg.timeout}
            return {"tool": tool_name, "status": "not_found"}
        except Exception:
            return {"tool": tool_name, "status": "unknown"}

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_tool_available", False) else "degraded",
            "version": self.version,
        }