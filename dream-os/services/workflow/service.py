"""Workflow Service - 工作流编排服务"""
from ..base import BaseService


class WorkflowService(BaseService):
    name = "workflow"
    
    async def run(self, workflow_type: str, context: dict = None) -> dict:
        """运行工作流"""
        return {"workflow": workflow_type, "status": "delegated"}
