"""Tool Center — 统一工具管理中心

功能：
1. Tool 配置管理 — 每个工具独立配置（超时、重试、安全级别、启用/禁用）
2. 执行历史存储 — 持久化记录所有执行记录
3. 健康监控 — 可用性、失败率、平均耗时追踪
4. 自动发现 — 自动检测新注册的工具
"""

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime, timedelta
from collections import defaultdict, deque

from ..core.tool_registry import ToolRegistry, ToolExecutionRecord, ToolStatus
from ..tools import ToolManager

logger = logging.getLogger("dream-os.tool_center")

# ── 默认配置 ──────────────────────────────

DEFAULT_TOOL_CONFIGS = {
    "shell_exec":     {"timeout": 120, "retry_count": 1, "security_level": "high",  "enabled": True},
    "file_read":      {"timeout": 30,  "retry_count": 1, "security_level": "medium","enabled": True},
    "file_write":     {"timeout": 30,  "retry_count": 0, "security_level": "high",  "enabled": True},
    "file_list":      {"timeout": 15,  "retry_count": 1, "security_level": "low",   "enabled": True},
    "http_fetch":     {"timeout": 15,  "retry_count": 2, "security_level": "low",   "enabled": True},
    "stock_query":    {"timeout": 20,  "retry_count": 2, "security_level": "low",   "enabled": True},
    "weather_query":  {"timeout": 15,  "retry_count": 2, "security_level": "low",   "enabled": True},
    "python_exec":    {"timeout": 60,  "retry_count": 1, "security_level": "high",  "enabled": True},
    "browser_fetch":  {"timeout": 30,  "retry_count": 1, "security_level": "low",   "enabled": True},
    "image_generate": {"timeout": 120, "retry_count": 1, "security_level": "low",   "enabled": True},
}


# ── 工具配置 ──────────────────────────────

@dataclass
class ToolConfig:
    """单个工具的运行时配置"""
    name: str
    timeout: int = 30
    retry_count: int = 1
    security_level: str = "medium"  # low / medium / high
    enabled: bool = True
    description: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ToolConfig":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})


# ── 健康状态 ──────────────────────────────

@dataclass
class ToolHealth:
    """工具的实时健康状态"""
    name: str
    total_executions: int = 0
    success_count: int = 0
    failed_count: int = 0
    timeout_count: int = 0
    avg_duration_ms: float = 0.0
    last_execution: Optional[float] = None
    last_error: str = ""
    consecutive_failures: int = 0
    uptime_status: str = "unknown"  # healthy / degraded / down

    @property
    def failure_rate(self) -> float:
        if self.total_executions == 0:
            return 0.0
        return round((self.failed_count + self.timeout_count) / self.total_executions * 100, 1)

    @property
    def is_healthy(self) -> bool:
        return self.failure_rate < 30.0 and self.consecutive_failures < 3

    def record(self, record: ToolExecutionRecord):
        self.total_executions += 1
        if record.status == ToolStatus.SUCCESS:
            self.success_count += 1
            self.consecutive_failures = 0
        elif record.status == ToolStatus.FAILED:
            self.failed_count += 1
            self.consecutive_failures += 1
            self.last_error = record.error[:200]
        elif record.status == ToolStatus.TIMEOUT:
            self.timeout_count += 1
            self.consecutive_failures += 1
            self.last_error = f"超时 ({record.duration_ms}ms)"

        self.last_execution = record.end_time or time.time()
        # Moving average
        if self.total_executions <= 1:
            self.avg_duration_ms = record.duration_ms
        else:
            self.avg_duration_ms = self.avg_duration_ms * 0.7 + record.duration_ms * 0.3

        # Determine status
        if self.consecutive_failures >= 5:
            self.uptime_status = "down"
        elif self.consecutive_failures >= 3:
            self.uptime_status = "degraded"
        else:
            self.uptime_status = "healthy"

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "total_executions": self.total_executions,
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "timeout_count": self.timeout_count,
            "failure_rate": self.failure_rate,
            "avg_duration_ms": round(self.avg_duration_ms, 1),
            "last_execution": self.last_execution,
            "last_error": self.last_error[:100] if self.last_error else "",
            "consecutive_failures": self.consecutive_failures,
            "uptime_status": self.uptime_status,
            "is_healthy": self.is_healthy,
        }


# ── 执行历史存储 ──────────────────────────────

class ExecutionHistoryStore:
    """执行历史存储（内存 + 后续可扩展为数据库存储）"""

    MAX_HISTORY = 1000  # 最多保留 1000 条

    def __init__(self):
        self._records: deque[ToolExecutionRecord] = deque(maxlen=self.MAX_HISTORY)

    def append(self, record: ToolExecutionRecord):
        self._records.append(record)

    def get_recent(self, limit: int = 50) -> list[dict]:
        records = list(self._records)[-limit:]
        return [r.to_dict() for r in reversed(records)]

    def get_by_tool(self, tool_name: str, limit: int = 20) -> list[dict]:
        records = [r for r in self._records if r.tool_name == tool_name]
        return [r.to_dict() for r in reversed(records[-limit:])]

    def get_recent_by_status(self, status: str, limit: int = 20) -> list[dict]:
        records = [r for r in self._records if r.status == status]
        return [r.to_dict() for r in reversed(records[-limit:])]

    def clear(self):
        self._records.clear()

    @property
    def count(self) -> int:
        return len(self._records)


# ── Tool Center ──────────────────────────────

class ToolCenter:
    """Tool Center 主管理器

    封装 ToolRegistry，增加：
    - 工具配置管理
    - 执行历史记录
    - 健康监控
    - 自动发现
    """

    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self.history = ExecutionHistoryStore()
        self.health: dict[str, ToolHealth] = {}
        self.configs: dict[str, ToolConfig] = {}
        self._init_configs()

    def _init_configs(self):
        """初始化所有已注册工具配置"""
        for tool_info in self.registry.list_tools():
            name = tool_info["name"]
            default = DEFAULT_TOOL_CONFIGS.get(name, {})
            self.configs[name] = ToolConfig(
                name=name,
                timeout=default.get("timeout", 30),
                retry_count=default.get("retry_count", 1),
                security_level=default.get("security_level", "medium"),
                enabled=default.get("enabled", True),
                description=tool_info.get("description", ""),
            )
            self.health[name] = ToolHealth(name=name)
        logger.info(f"ToolCenter initialized with {len(self.configs)} tools")

    # ── 自动发现 ──────────────────────────────

    def discover(self) -> list[str]:
        """自动发现新注册的工具

        扫描 Registry，注册缺失的工具配置和健康监控。
        新增工具不需要修改 Agent 代码。

        Returns:
            新发现的工具名称列表
        """
        discovered = []
        for tool_info in self.registry.list_tools():
            name = tool_info["name"]
            if name not in self.configs:
                default = DEFAULT_TOOL_CONFIGS.get(name, {})
                self.configs[name] = ToolConfig(
                    name=name,
                    timeout=default.get("timeout", 30),
                    retry_count=default.get("retry_count", 1),
                    security_level=default.get("security_level", "medium"),
                    enabled=default.get("enabled", True),
                    description=tool_info.get("description", ""),
                )
                self.health[name] = ToolHealth(name=name)
                discovered.append(name)
                logger.info(f"ToolCenter discovered new tool: {name}")
        return discovered

    # ── 配置管理 ──────────────────────────────

    def get_config(self, name: str) -> Optional[ToolConfig]:
        return self.configs.get(name)

    def update_config(self, name: str, updates: dict) -> Optional[ToolConfig]:
        """更新工具配置"""
        cfg = self.configs.get(name)
        if not cfg:
            return None
        for key, value in updates.items():
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        logger.info(f"Tool config updated: {name} → {json.dumps(updates, ensure_ascii=False)}")
        return cfg

    def list_configs(self) -> list[dict]:
        """列出所有工具配置（含健康状态）"""
        # 先发现新工具
        self.discover()
        result = []
        for name in sorted(self.configs.keys()):
            cfg = self.configs[name]
            health = self.health.get(name)
            entry = cfg.to_dict()
            if health:
                entry["health"] = health.to_dict()
            result.append(entry)
        return result

    # ── 执行与记录 ──────────────────────────────

    async def execute(self, tool_name: str, command: str,
                      timeout: Optional[int] = None) -> ToolExecutionRecord:
        """执行工具，自动记录历史 + 更新健康状态"""
        cfg = self.configs.get(tool_name)
        if cfg and not cfg.enabled:
            record = ToolExecutionRecord(
                tool_name=tool_name,
                command=command,
                status=ToolStatus.FAILED,
                error=f"工具 '{tool_name}' 已被禁用",
                start_time=time.time(),
                end_time=time.time(),
                duration_ms=0,
            )
            self.history.append(record)
            return record

        actual_timeout = timeout or (cfg.timeout if cfg else 30)
        record = await self.registry.execute(tool_name, command, timeout=actual_timeout)

        # 记录历史
        self.history.append(record)

        # 更新健康状态
        health = self.health.get(tool_name)
        if health:
            health.record(record)

        return record

    # ── 查询 ──────────────────────────────

    def get_history(self, limit: int = 50) -> list[dict]:
        return self.history.get_recent(limit)

    def get_tool_history(self, tool_name: str, limit: int = 20) -> list[dict]:
        return self.history.get_by_tool(tool_name, limit)

    def get_health_summary(self) -> dict:
        """获取所有工具的健康摘要"""
        self.discover()
        healthy = sum(1 for h in self.health.values() if h.is_healthy)
        degraded = sum(1 for h in self.health.values() if h.uptime_status == "degraded")
        down = sum(1 for h in self.health.values() if h.uptime_status == "down")
        total_exec = sum(h.total_executions for h in self.health.values())
        total_fail = sum(h.failed_count + h.timeout_count for h in self.health.values())

        return {
            "total_tools": len(self.health),
            "healthy": healthy,
            "degraded": degraded,
            "down": down,
            "total_executions": total_exec,
            "total_failures": total_fail,
            "overall_failure_rate": round(total_fail / total_exec * 100, 1) if total_exec > 0 else 0,
            "history_count": self.history.count,
            "tools": [h.to_dict() for h in self.health.values()],
        }

    def get_dashboard(self) -> dict:
        """获取 Tool Center 完整仪表盘数据"""
        return {
            "configs": self.list_configs(),
            "status": self.get_health_summary(),
            "recent_history": self.get_history(20),
        }

    # ── 测试工具 ──────────────────────────────

    async def test_tool(self, tool_name: str, command: str = "") -> ToolExecutionRecord:
        """测试工具运行状态"""
        cfg = self.configs.get(tool_name)
        if not cfg:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILED,
                error=f"工具 '{tool_name}' 未注册",
            )

        # 使用默认测试命令
        if not command:
            test_commands = {
                "shell_exec": "echo 'Tool Center test OK'",
                "file_read": "cat /etc/hostname 2>/dev/null || echo 'no hostname'",
                "file_write": "",
                "file_list": "ls /app 2>/dev/null || echo 'no /app'",
                "http_fetch": "GET https://httpbin.org/get",
                "stock_query": "GET https://qt.gtimg.cn/q=sh000001",
                "weather_query": "GET https://wttr.in/beijing?format=%T+%C+%h+%w",
                "python_exec": "print('Python test OK')",
                "browser_fetch": "GET https://example.com",
                "image_generate": "",
            }
            command = test_commands.get(tool_name, "")

        if not command:
            return ToolExecutionRecord(
                tool_name=tool_name,
                status=ToolStatus.FAILED,
                error=f"工具 '{tool_name}' 无测试命令",
            )

        return await self.execute(tool_name, command)


# ── 全局实例 ──────────────────────────────

_tool_center: Optional[ToolCenter] = None


def get_tool_center() -> ToolCenter:
    """获取全局 ToolCenter 单例"""
    global _tool_center
    if _tool_center is None:
        _tool_center = ToolCenter()
    return _tool_center