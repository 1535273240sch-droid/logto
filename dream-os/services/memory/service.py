"""Memory Service - 记忆管理服务"""
from typing import Optional, Any
from ..base import BaseService


class MemoryService(BaseService):
    name = "memory"
    version = "1.0.0"

    async def initialize(self):
        try:
            from dream_os.backend.app.db.session import get_db
            self._session_available = True
        except ImportError:
            self._session_available = False
        return self

    async def save_message(self, conversation_id, role, content, metadata=None):
        try:
            from dream_os.backend.app.db.session import get_db
            from dream_os.backend.app.models.memory import Message
            from datetime import datetime
            async for session in get_db():
                msg = Message(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    created_at=datetime.utcnow(),
                )
                session.add(msg)
                await session.commit()
                await session.refresh(msg)
                return {"id": msg.id, "status": "ok"}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    async def get_conversation_messages(self, conversation_id, limit=50):
        try:
            from dream_os.backend.app.db.session import get_db
            from dream_os.backend.app.models.memory import Message
            from sqlalchemy import select, desc
            async for session in get_db():
                result = await session.execute(
                    select(Message).where(Message.conversation_id == conversation_id)
                    .order_by(desc(Message.created_at)).limit(limit)
                )
                messages = result.scalars().all()
                return [{"id": m.id, "role": m.role, "content": m.content,
                         "created_at": str(m.created_at) if m.created_at else ""}
                        for m in reversed(messages)]
        except Exception as e:
            return []

    async def save_memory(self, user_id, key, value, category="auto_extracted", importance=5):
        try:
            from dream_os.backend.app.db.session import get_db
            from dream_os.backend.app.models.memory import Memory
            from sqlalchemy import select
            async for session in get_db():
                result = await session.execute(
                    select(Memory).where(Memory.user_id == user_id, Memory.key == key)
                )
                existing = result.scalar_one_or_none()
                if existing:
                    existing.value = value
                    existing.importance = importance
                else:
                    memory = Memory(
                        user_id=user_id, key=key, value=value,
                        category=category, importance=importance,
                    )
                    session.add(memory)
                await session.commit()
                return {"status": "ok", "key": key}
        except Exception as e:
            return {"status": "error", "error": str(e)[:200]}

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_session_available", False) else "degraded",
            "version": self.version,
        }