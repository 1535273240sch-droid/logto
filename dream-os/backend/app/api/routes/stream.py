"""Stream Route - SSE 流式对话端点"""
import json
import uuid
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.agent_loop import AgentLoop
from ...db.session import get_db

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "agnes-2.0-flash"
    mode: Optional[str] = "chat"
    conversation_id: Optional[str] = ""


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    mode = request.mode or "chat"
    conversation_id = request.conversation_id or str(uuid.uuid4())[:8]

    loop = AgentLoop(db=db)

    async def event_generator():
        if mode == "dev":
            async for event in loop.run_dev(request.message):
                yield event
        else:
            async for event in loop.run_chat(request.message):
                yield event

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/api/health")
async def health():
    return {"status": "ok", "service": "dream-os-backend"}
