"""Event Bus - 模块间事件通信总线"""
from typing import Callable, Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import asyncio
import fnmatch


@dataclass
class Event:
    type: str
    source: str
    data: Any = None
    priority: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


class EventBus:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[str, List[Callable]] = {}
            cls._instance._history: List[Event] = []
            cls._instance._max_history = 1000
        return cls._instance

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable):
        if event_type in self._subscribers:
            self._subscribers[event_type] = [cb for cb in self._subscribers[event_type] if cb != callback]

    async def publish(self, event: Event):
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history.pop(0)

        for pattern, callbacks in self._subscribers.items():
            if fnmatch.fnmatch(event.type, pattern):
                for callback in callbacks:
                    try:
                        if asyncio.iscoroutinefunction(callback):
                            await callback(event)
                        else:
                            callback(event)
                    except Exception as e:
                        print(f"[EventBus] Error in subscriber for {event.type}: {e}")

    def get_history(self, event_type: Optional[str] = None, limit: int = 50) -> List[Event]:
        if event_type:
            return [e for e in self._history if e.type == event_type][-limit:]
        return self._history[-limit:]


def get_event_bus() -> EventBus:
    return EventBus()