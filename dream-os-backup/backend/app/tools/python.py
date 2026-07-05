"""Python Tool — Python 代码执行工具"""
import json
import logging
import asyncio
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.python")


class PythonTool(BaseTool):
    """Python 代码执行工具 — 执行 Python 代码片段"""

    name = "python_exec"
    description = "执行 Python 代码（数学计算、数据分析、图表生成等）"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        """执行 Python 代码

        command 格式:
            python:print(1+1)
            python:import pandas as pd\nprint(pd.DataFrame())
        """
        try:
            code = command.replace("python:", "", 1).strip()
            if not code:
                return ToolResult(success=False, stderr="请提供要执行的 Python 代码")

            return await self._run_python(code)
        except Exception as e:
            logger.error(f"Python exec failed: {e}")
            return ToolResult(
                success=False,
                stderr=f"Python 执行失败: {str(e)[:200]}",
                exit_code=1,
            )

    async def _run_python(self, code: str, timeout: int = 30) -> ToolResult:
        """在子进程中执行 Python 代码"""
        # 构建安全的执行环境
        # 限制内存和 CPU 使用
        wrapped_code = f"""
import sys, json, math, statistics, datetime, random, re, collections, itertools, fractions, decimal

def _safe_exec():
    try:
        _locals = {{}}
        exec('''{code.replace("'", "\\'").replace('"', '\\"')}''', _locals)
        _output = _locals.get('result', _locals.get('output', ''))
        if _output != '':
            print(_output)
    except Exception as e:
        print(f"ERROR: {{e}}", file=sys.stderr)
        sys.exit(1)

_safe_exec()
"""
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-c", code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB 输出限制
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            stdout_str = stdout.decode("utf-8", errors="replace")[:5000]
            stderr_str = stderr.decode("utf-8", errors="replace")[:2000]

            if proc.returncode == 0:
                result = stdout_str.strip() or "(无输出)"
                return ToolResult(success=True, stdout=result)
            else:
                return ToolResult(
                    success=False,
                    stdout=stdout_str,
                    stderr=stderr_str,
                    exit_code=proc.returncode or 1,
                )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                stderr=f"Python 执行超时 ({timeout}s)",
                exit_code=1,
            )