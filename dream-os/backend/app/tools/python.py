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
        safe_code = code.replace("'", "\\'").replace('"', '\\"')
        wrapped_code = (
            "import sys, json, math, statistics, datetime, random, re, collections, itertools, fractions, decimal\n"
            "\n"
            "def _safe_exec():\n"
            "    try:\n"
            "        _locals = {}\n"
            f"        exec('''{safe_code}''', _locals)\n"
            "        _output = _locals.get('result', _locals.get('output', ''))\n"
            "        if _output != '':\n"
            "            print(_output)\n"
            "    except Exception as e:\n"
            "        print(f'ERROR: {e}', file=sys.stderr)\n"
            "        sys.exit(1)\n"
            "\n"
            "_safe_exec()\n"
        )
        try:
            proc = await asyncio.create_subprocess_exec(
                "python3", "-c", wrapped_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,
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
