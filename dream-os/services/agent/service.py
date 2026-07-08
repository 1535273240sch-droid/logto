"""Agent Service - AI Agent 管理服务"""
from typing import Optional
from ..base import BaseService


class AgentService(BaseService):
    name = "agent"
    version = "1.0.0"

    async def initialize(self):
        try:
            from dream_os.backend.app.core.agent_loop import AgentLoop
            from dream_os.backend.app.core.tool_registry import ToolRegistry
            self._agent_available = True
        except ImportError:
            self._agent_available = False
        return self

    async def execute(self, agent_type, task, context=None):
        try:
            from dream_os.backend.app.core.agent_loop import AgentLoop
            loop = AgentLoop()
            result = await loop.run(task)
            return {
                "status": "completed",
                "agent_type": agent_type,
                "result": result[:2000] if isinstance(result, str) else str(result)[:2000],
            }
        except Exception as e:
            return {"status": "error", "agent_type": agent_type, "error": str(e)[:200]}

    async def get_status(self, task_id):
        return {"task_id": task_id, "status": "unknown"}

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_agent_available", False) else "degraded",
            "version": self.version,
        }