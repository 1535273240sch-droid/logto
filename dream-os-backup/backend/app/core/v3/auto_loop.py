"""AutoLoop — 自主循环引擎

封装 Orchestrator 的自主修复循环:
  1. 首轮: 完整执行 Planner → Architect → Coder → Executor → Reviewer → Tester → Deployer → Reporter
  2. 如果 Reviewer 发现严重问题 或 Tester 失败:
     → 返回 Coder 修复
     → 重新执行 Executor → Reviewer → Tester
  3. 循环直到测试通过或达到最大迭代次数

Bug 自动修复:
  - 读取执行日志和错误信息
  - 将错误信息注入 Coder 的上下文
  - Coder 根据错误信息修改代码
  - 重新执行验证
"""
import logging
import asyncio
from typing import Callable, Awaitable

from .orchestrator import Orchestrator, OrchestratorState
from .blackboard import SharedBlackboard
from .base_agent import EventCallback

logger = logging.getLogger("dream-os.v3.autoloop")


class AutoLoop:
    """自主循环引擎"""

    def __init__(self, tool_manager):
        self.tool_manager = tool_manager
        self.orchestrator = Orchestrator(tool_manager)

    async def run(
        self,
        requirement: str,
        task_id: str,
        emit: EventCallback,
        max_iterations: int = 3,
    ) -> dict:
        """执行自主开发循环

        Args:
            requirement: 用户需求
            task_id: 任务 ID
            emit: SSE 事件回调
            max_iterations: 最大修复迭代次数

        Returns:
            执行结果字典
        """
        logger.info(f"AutoLoop started: task={task_id}, requirement={requirement[:100]}")

        result = await self.orchestrator.run(
            requirement=requirement,
            task_id=task_id,
            emit=emit,
            max_iterations=max_iterations,
        )

        logger.info(f"AutoLoop completed: success={result['success']}")
        return result

    def get_state(self) -> dict:
        """获取当前状态"""
        return {
            "state": self.orchestrator.state.value,
            "iteration": self.orchestrator.blackboard.iteration,
            "max_iterations": self.orchestrator.blackboard.max_iterations,
            "blackboard": self.orchestrator.blackboard.summary(),
            "workspace": self.orchestrator.blackboard.workspace_path,
        }

    def get_workspace_files(self) -> list[dict]:
        """获取工作空间文件"""
        return self.orchestrator.get_workspace_files()

    def get_blackboard(self) -> SharedBlackboard:
        return self.orchestrator.blackboard
