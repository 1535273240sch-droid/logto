"""Tool Registry — 统一工具注册中心

支持：
- 按 Intent 自动路由到对应 Tool
- 多工具链编排
- 状态管理 (Waiting/Running/Success/Failed/Timeout)
- 自动发现新注册的工具
- 新工具无需修改 Planner，Router 自动发现
"""
import time
import json
import logging
from dataclasses import dataclass, field
from typing import Optional, Callable
from ..tools import ToolManager, BaseTool
from ..tools import ShellTool, FileTool, HttpTool
from ..tools import StockTool, WeatherTool, PythonTool, BrowserTool, ImageTool

logger = logging.getLogger("dream-os.tool_registry")

# ── 工具状态 ──────────────────────────────

class ToolStatus:
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


@dataclass
class ToolExecutionRecord:
    """单次工具执行记录"""
    tool_name: str
    intent: str = ""
    command: str = ""
    status: str = ToolStatus.WAITING
    result: str = ""
    error: str = ""
    start_time: float = 0.0
    end_time: float = 0.0
    duration_ms: int = 0
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "tool": self.tool_name,
            "intent": self.intent,
            "command": self.command[:200],
            "status": self.status,
            "result_preview": self.result[:200],
            "error": self.error[:200] if self.error else "",
            "duration_ms": self.duration_ms,
        }


# ── Intent → Tool 映射 ──────────────────────────────

_INTENT_TOOL_MAP = {
    "real_time_data": [
        "stock_query",          # 股票
        "weather_query",        # 天气
        "http_fetch",           # 通用HTTP查询（黄金、新闻等）
        "shell_exec",           # 备用
    ],
    "file_operation": ["file_read", "file_write", "file_list", "shell_exec"],
    "shell": ["shell_exec"],
    "image": ["image_generate", "shell_exec"],   # image_generate 优先
    "math": ["python_exec", "shell_exec"],        # python_exec 优先
    "code": ["python_exec", "file_write", "file_read", "shell_exec"],
    "search": ["http_fetch", "browser_fetch"],
    "browser": ["browser_fetch", "http_fetch"],
    "chat": [],
    "memory": [],
    "complex": [
        "http_fetch", "browser_fetch", "stock_query", "weather_query",
        "python_exec", "shell_exec", "file_read", "file_write",
        "image_generate",
    ],
    "unknown": ["http_fetch", "shell_exec"],
}


class ToolRegistry:
    """统一工具注册中心

    Router 自动发现已注册工具，按 Intent 路由。
    新增 Tool 只需注册到这里，Planner 不需要修改。
    """

    def __init__(self):
        self._tm = ToolManager()
        self._register_defaults()

    def _register_defaults(self):
        """注册所有默认工具"""
        # 基础工具
        self.register(ShellTool())
        self.register(FileTool())
        self.register(HttpTool())

        # V1.5 新增工具
        self.register(StockTool())
        self.register(WeatherTool())
        self.register(PythonTool())
        self.register(BrowserTool())
        self.register(ImageTool())

        logger.info(f"ToolRegistry: {len(self._tm.list_names())} tools registered")

    def register(self, tool: BaseTool):
        """注册工具"""
        self._tm.register(tool)
        logger.debug(f"Tool registered: {tool.name}")

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tm.get(name)

    def list_tools(self) -> list[dict]:
        return self._tm.list_tools()

    def list_schemas(self) -> list[dict]:
        return self._tm.list_schemas()

    def list_names(self) -> list[str]:
        return self._tm.list_names()

    # ── Router: Intent → Tool ──────────────────────────────

    def route(self, intent: str) -> list[str]:
        """根据意图路由到对应工具列表

        Args:
            intent: 意图类型字符串

        Returns:
            可用工具名称列表（仅返回已注册的）
        """
        tools = _INTENT_TOOL_MAP.get(intent, _INTENT_TOOL_MAP["unknown"])
        available = [t for t in tools if self._tm.get(t)]
        if not available and intent not in ("chat", "memory"):
            logger.warning(f"Intent '{intent}' has no available tools, fallback to shell")
            available = ["shell_exec"] if self._tm.get("shell_exec") else []
        return available

    def get_tool_for_command(self, command: str) -> Optional[str]:
        """根据命令内容自动选择工具"""
        cmd = command.strip().lower()

        # 工具前缀匹配
        if cmd.startswith("stock:"):
            return "stock_query" if self._tm.get("stock_query") else None
        if cmd.startswith("weather:"):
            return "weather_query" if self._tm.get("weather_query") else None
        if cmd.startswith("python:"):
            return "python_exec" if self._tm.get("python_exec") else None
        if cmd.startswith("browser:"):
            return "browser_fetch" if self._tm.get("browser_fetch") else None
        if cmd.startswith("image:"):
            return "image_generate" if self._tm.get("image_generate") else None
        if cmd.startswith("crypto:"):
            return "stock_query" if self._tm.get("stock_query") else None

        # HTTP 请求
        if cmd.startswith("get ") or cmd.startswith("post ") or cmd.startswith("http"):
            return "http_fetch" if self._tm.get("http_fetch") else None

        # 文件操作
        if any(cmd.startswith(p) for p in ["cat ", "head ", "tail ", "wc ", "ls ", "find "]):
            return "shell_exec" if self._tm.get("shell_exec") else None

        # 默认 shell
        if self._tm.get("shell_exec"):
            return "shell_exec"
        return None

    # ── Executor: 执行工具 + 状态管理 ──────────────────────────────

    async def execute(self, tool_name: str, command: str,
                      timeout: int = 30) -> ToolExecutionRecord:
        """执行工具，自动管理状态（Waiting → Running → Success/Failed/Timeout）

        Args:
            tool_name: 工具名称
            command: 要执行的命令
            timeout: 超时时间（秒）

        Returns:
            ToolExecutionRecord 包含完整执行记录
        """
        record = ToolExecutionRecord(
            tool_name=tool_name,
            command=command,
            status=ToolStatus.WAITING,
            start_time=time.time(),
        )

        tool = self._tm.get(tool_name)
        if not tool:
            record.status = ToolStatus.FAILED
            record.error = f"工具 '{tool_name}' 未注册"
            record.end_time = time.time()
            record.duration_ms = int((record.end_time - record.start_time) * 1000)
            logger.warning(f"Tool '{tool_name}' not found in registry")
            return record

        # 状态: RUNNING
        record.status = ToolStatus.RUNNING

        try:
            import asyncio
            result = await asyncio.wait_for(
                tool.execute(command, timeout=timeout),
                timeout=timeout + 5,
            )
            record.end_time = time.time()
            record.duration_ms = int((record.end_time - record.start_time) * 1000)

            if result.success:
                record.status = ToolStatus.SUCCESS
                record.result = result.stdout[:5000]
            else:
                record.status = ToolStatus.FAILED
                record.error = result.stderr[:2000]
                record.result = result.stdout[:2000]

            record.extra = result.extra

        except asyncio.TimeoutError:
            record.status = ToolStatus.TIMEOUT
            record.error = f"工具执行超时 ({timeout}s)"
            record.end_time = time.time()
            record.duration_ms = int((record.end_time - record.start_time) * 1000)

        except Exception as e:
            record.status = ToolStatus.FAILED
            record.error = str(e)[:2000]
            record.end_time = time.time()
            record.duration_ms = int((record.end_time - record.start_time) * 1000)

        logger.info(
            f"Tool '{tool_name}' → {record.status} "
            f"({record.duration_ms}ms, {len(record.result)} chars)"
        )
        return record

    def to_pipeline_log(self, records: list[ToolExecutionRecord]) -> list[dict]:
        """转换为可记录的结构化日志"""
        return [r.to_dict() for r in records]