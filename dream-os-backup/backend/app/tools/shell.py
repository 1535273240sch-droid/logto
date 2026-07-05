"""Shell Tool - 安全执行 Linux Shell 命令"""
import asyncio
import os
from .base import BaseTool, ToolResult


class ShellTool(BaseTool):
    """在 Linux 服务器上执行 Shell 命令"""

    name = "shell_exec"
    description = (
        "在 Linux 服务器上执行任意 Shell 命令。"
        "支持：文件操作、服务管理、软件安装、进程管理等。"
        "命令会在 /workspace 目录下执行。"
    )

    def __init__(self, work_dir: str = "/workspace"):
        self.work_dir = work_dir

    async def execute(self, command: str, timeout: int = 120, **kwargs) -> ToolResult:
        # 确保工作目录存在
        work_dir = self.work_dir
        if not os.path.isdir(work_dir):
            work_dir = "/tmp"
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
                env={**os.environ, "DEBIAN_FRONTEND": "noninteractive"},
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
            return ToolResult(
                success=proc.returncode == 0,
                stdout=stdout.decode("utf-8", errors="replace"),
                stderr=stderr.decode("utf-8", errors="replace"),
                exit_code=proc.returncode or 0,
            )
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                stderr=f"命令执行超时 ({timeout}s): {command}",
                exit_code=124,
            )
        except Exception as e:
            return ToolResult(
                success=False,
                stderr=str(e),
                exit_code=1,
            )


class ShellToolSafe(ShellTool):
    """安全的 Shell 工具，添加命令白名单"""

    name = "shell_safe"
    description = "安全 Shell 执行，命令被限制在白名单范围内"

    ALLOWED_PREFIXES = [
        "echo", "ls", "cat", "head", "tail", "wc",
        "df", "du", "free", "uptime", "uname", "hostname",
        "whoami", "id", "date", "pwd",
        "mkdir", "touch", "cp", "mv", "rm",
        "python", "python3", "pip", "pip3",
        "git", "docker", "docker-compose",
        "systemctl", "journalctl",
        "curl", "wget",
        "npm", "node", "yarn", "pnpm",
        "apt-get", "apt",
        "find", "grep", "sed", "awk",
        "chmod", "chown",
        "ss", "netstat", "ps", "top",
        "kill", "pkill",
        "ssh", "scp",
        "tar", "gzip", "unzip", "zip",
    ]

    async def execute(self, command: str, timeout: int = 120, **kwargs) -> ToolResult:
        cmd_prefix = command.strip().split()[0] if command.strip() else ""
        cmd_base = cmd_prefix.split("/")[-1]  # 去除路径前缀

        if cmd_base not in self.ALLOWED_PREFIXES:
            return ToolResult(
                success=False,
                stderr=f"命令 '{cmd_base}' 不在允许列表中",
                exit_code=1,
            )

        return await super().execute(command, timeout, **kwargs)
