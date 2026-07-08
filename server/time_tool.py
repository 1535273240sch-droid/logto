"""Time Tool — 时间查询工具"""
import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from ..tools.base import BaseTool, ToolResult

logger = logging.getLogger("dream-os.tools.time")

WEEKDAYS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


class TimeTool(BaseTool):
    """时间查询工具 — 返回北京时间"""

    name = "time_query"
    description = "查询当前北京时间（Asia/Shanghai）的日期、时间、星期"

    async def execute(self, command: str, **kwargs) -> ToolResult:
        try:
            tz = ZoneInfo("Asia/Shanghai")
            now = datetime.now(tz)
            data = {
                "datetime": now.strftime("%Y-%m-%d %H:%M:%S"),
                "date": now.strftime("%Y年%m月%d日"),
                "time": now.strftime("%H:%M:%S"),
                "weekday": WEEKDAYS[now.weekday()],
                "timezone": "Asia/Shanghai",
                "timestamp": int(now.timestamp()),
            }
            return ToolResult(success=True, stdout=json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Time query failed: {e}")
            return ToolResult(success=False, stderr=f"时间查询失败: {str(e)[:200]}")
