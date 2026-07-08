"""Chat Service - 对话管理服务"""
from typing import AsyncGenerator, Optional
from ..base import BaseService


class ChatService(BaseService):
    name = "chat"
    version = "1.0.0"

    async def initialize(self):
        try:
            from dream_os.backend.app.core.ai_provider import get_ai_client
            from dream_os.backend.app.core.agent_loop import AgentLoop
            self._ai_available = True
        except ImportError:
            self._ai_available = False
        return self

    async def stream_chat(self, message, conversation_id="", mode="chat", **kwargs):
        yield "data: {{routing to backend stream endpoint}}"

    async def send_message(self, conversation_id, content, role="user"):
        try:
            from dream_os.backend.app.db.session import get_db
            from dream_os.backend.app.models.memory import Message, Conversation
            from datetime import datetime
            from sqlalchemy import select
            async for session in get_db():
                result = await session.execute(
                    select(Conversation).where(Conversation.id == conversation_id)
                )
                conv = result.scalar_one_or_none()
                if not conv:
                    conv = Conversation(id=conversation_id, title=content[:50])
                    session.add(conv)
                    await session.flush()
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

    async def health_check(self):
        return {
            "name": self.name,
            "status": "healthy" if getattr(self, "_ai_available", False) else "degraded",
            "version": self.version,
        }