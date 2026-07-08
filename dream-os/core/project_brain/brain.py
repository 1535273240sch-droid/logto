"""Project Brain - 项目状态内核"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field

from .state import ProjectState
from ..event_bus import EventBus, Event


@dataclass
class WorkLog:
    agent: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    details: Optional[Dict[str, Any]] = None


class ProjectBrain:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def initialize(self, project_id: str = "dream-os-v6", name: str = "Dream OS V6"):
        if self._initialized:
            return
        self.state = ProjectState(project_id=project_id, name=name)
        self.work_logs: List[WorkLog] = []
        self.event_bus = EventBus()
        self._data_dir = "/workspace/dream-os/data"
        self._initialized = True

        self.event_bus.subscribe("agent.*", self._on_agent_event)

    async def _on_agent_event(self, event: Event):
        if event.type == "agent.start":
            self.state.last_agent = event.data.get("agent", "")
            self.state.last_updated = datetime.utcnow().isoformat()
        elif event.type == "agent.complete":
            self.work_logs.append(WorkLog(
                agent=event.data.get("agent", ""),
                action=event.data.get("action", "completed"),
                details=event.data.get("result"),
            ))

    def get_state(self) -> ProjectState:
        return self.state

    def get_summary(self) -> str:
        return self.state.summary()

    async def update_state(self, updates: Dict[str, Any]):
        for key, value in updates.items():
            if hasattr(self.state, key):
                setattr(self.state, key, value)
        self.state.last_updated = datetime.utcnow().isoformat()
        await self.event_bus.publish(Event(
            type="project.updated",
            source="project_brain",
            data={"updates": updates},
        ))

    async def agent_start(self, agent_name: str, task: str):
        await self.event_bus.publish(Event(
            type="agent.start",
            source="project_brain",
            data={"agent": agent_name, "task": task},
        ))

    async def agent_complete(self, agent_name: str, result: Any):
        await self.event_bus.publish(Event(
            type="agent.complete",
            source="project_brain",
            data={"agent": agent_name, "result": result},
        ))

    def search_logs(self, agent: Optional[str] = None, limit: int = 10) -> List[WorkLog]:
        logs = self.work_logs
        if agent:
            logs = [l for l in logs if l.agent == agent]
        return logs[-limit:]

    def save(self):
        os.makedirs(self._data_dir, exist_ok=True)
        path = os.path.join(self._data_dir, "project_state.json")
        with open(path, "w") as f:
            json.dump({
                "state": {
                    "project_id": self.state.project_id,
                    "name": self.state.name,
                    "phase": self.state.phase,
                    "progress_percent": self.state.progress_percent,
                    "completed_tasks": self.state.completed_tasks,
                    "pending_tasks": self.state.pending_tasks,
                    "bugs": self.state.bugs,
                    "risks": self.state.risks,
                    "files": self.state.files,
                    "api_changes": self.state.api_changes,
                    "db_changes": self.state.db_changes,
                    "deploy_status": self.state.deploy_status,
                    "last_agent": self.state.last_agent,
                    "last_updated": self.state.last_updated,
                },
                "work_logs": [
                    {"agent": w.agent, "action": w.action, "timestamp": w.timestamp}
                    for w in self.work_logs[-100:]
                ],
            }, f, ensure_ascii=False, indent=2)

    def load(self):
        path = os.path.join(self._data_dir, "project_state.json")
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
            for key, value in data.get("state", {}).items():
                if hasattr(self.state, key):
                    setattr(self.state, key, value)
            for entry in data.get("work_logs", []):
                self.work_logs.append(WorkLog(
                    agent=entry.get("agent", ""),
                    action=entry.get("action", ""),
                    timestamp=entry.get("timestamp", ""),
                ))


def get_brain() -> ProjectBrain:
    return ProjectBrain()