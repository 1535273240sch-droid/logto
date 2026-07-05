"""Server Agent - 管理 Linux 服务器操作"""
import time
from .base import BaseAgent, ExecutionResult


class ServerAgent(BaseAgent):
    """负责 Linux 服务器上的所有操作"""

    name = "server"
    description = "Linux 服务器管理 Agent，可执行 Shell 命令、文件操作等"
    tools = ["shell", "file"]

    async def execute(self, step: dict, tool_manager) -> ExecutionResult:
        tool_name = step.get("tool", "shell")
        command = step.get("command", "")
        step_id = step.get("step", 0)
        step_name = step.get("name", "")

        tool = tool_manager.get(tool_name)
        if not tool:
            return ExecutionResult(
                step_id=step_id,
                step_name=step_name,
                agent=self.name,
                tool=tool_name,
                command=command,
                success=False,
                stderr=f"工具 '{tool_name}' 未注册",
                exit_code=1,
            )

        start = time.time()
        result = await tool.execute(command)
        duration = int((time.time() - start) * 1000)

        return ExecutionResult(
            step_id=step_id,
            step_name=step_name,
            agent=self.name,
            tool=tool_name,
            command=command,
            success=result.success,
            stdout=result.stdout,
            stderr=result.stderr,
            exit_code=result.exit_code,
            duration_ms=duration,
        )
