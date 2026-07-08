"""Work Log - 工作日志模块

自动记录每一步操作，永久保存，支持搜索和恢复。
"""
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Optional
from datetime import datetime

logger = logging.getLogger("dream-os.core.project_brain.log")


@dataclass
class LogEntry:
    """单条工作日志"""
    timestamp: str = ""
    agent: str = ""
    action: str = ""
    description: str = ""
    modified_files: list[str] = field(default_factory=list)
    added_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    duration_minutes: int = 0
    status: str = "completed"  # completed / failed / in_progress
    notes: str = ""

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "agent": self.agent,
            "action": self.action,
            "description": self.description[:200],
            "modified_files": self.modified_files[:10],
            "added_files": self.added_files[:10],
            "deleted_files": self.deleted_files[:10],
            "duration_minutes": self.duration_minutes,
            "status": self.status,
            "notes": self.notes[:200] if self.notes else "",
        }


class WorkLog:
    """工作日志 - 永久保存项目操作记录"""

    MAX_ENTRIES = 10000

    def __init__(self):
        self._entries: list[LogEntry] = []
        self._loaded = False

    def add_entry(self, entry: LogEntry):
        """添加日志条目"""
        if not entry.timestamp:
            entry.timestamp = datetime.now().isoformat()
        self._entries.append(entry)
        if len(self._entries) > self.MAX_ENTRIES:
            self._entries = self._entries[-self.MAX_ENTRIES:]
        logger.info(f"WorkLog: {entry.agent} → {entry.action}")

    def add(self, agent: str, action: str, description: str = "",
             modified_files: list[str] = None, **kwargs) -> LogEntry:
        """便捷方法：添加日志"""
        entry = LogEntry(
            timestamp=datetime.now().isoformat(),
            agent=agent,
            action=action,
            description=description,
            modified_files=modified_files or [],
            **{k: v for k, v in kwargs.items() if hasattr(LogEntry, k)},
        )
        self.add_entry(entry)
        return entry

    def get_recent(self, limit: int = 20) -> list[dict]:
        """获取最近的日志"""
        entries = self._entries[-limit:] if self._entries else []
        return [e.to_dict() for e in reversed(entries)]

    def get_by_agent(self, agent: str, limit: int = 50) -> list[dict]:
        """按 Agent 筛选"""
        entries = [e for e in self._entries if e.agent == agent]
        return [e.to_dict() for e in reversed(entries[-limit:])]

    def search(self, keyword: str, limit: int = 20) -> list[dict]:
        """搜索日志"""
        keyword = keyword.lower()
        matches = []
        for e in reversed(self._entries):
            if (keyword in e.agent.lower() or keyword in e.action.lower()
                    or keyword in e.description.lower()):
                matches.append(e.to_dict())
                if len(matches) >= limit:
                    break
        return matches

    def export(self) -> list[dict]:
        """导出所有日志"""
        return [e.to_dict() for e in self._entries]

    def clear(self):
        """清空日志"""
        self._entries.clear()

    @property
    def count(self) -> int:
        return len(self._entries)