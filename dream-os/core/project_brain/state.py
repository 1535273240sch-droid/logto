"""Project State - 项目状态数据模型"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class ProjectState:
    project_id: str
    name: str
    phase: str = "initialization"
    progress_percent: int = 0
    completed_tasks: List[str] = field(default_factory=list)
    pending_tasks: List[str] = field(default_factory=list)
    bugs: List[Dict[str, Any]] = field(default_factory=list)
    risks: List[str] = field(default_factory=list)
    files: List[str] = field(default_factory=list)
    api_changes: List[str] = field(default_factory=list)
    db_changes: List[str] = field(default_factory=list)
    deploy_status: str = "not_deployed"
    last_agent: str = ""
    last_updated: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    def summary(self) -> str:
        lines = [
            f"Project: {self.name} ({self.project_id})",
            f"Phase: {self.phase} | Progress: {self.progress_percent}%",
            f"Tasks: {len(self.completed_tasks)} completed, {len(self.pending_tasks)} pending",
            f"Bugs: {len(self.bugs)} | Risks: {len(self.risks)}",
            f"Deploy: {self.deploy_status}",
            f"Last Agent: {self.last_agent}",
            f"Last Updated: {self.last_updated}",
        ]
        return "\n".join(lines)