"""Stream Route - SSE 流式对话端点"""
import json
import uuid
import logging
from typing import Optional
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.agent_loop import AgentLoop
from ...tools.image import ImageTool
from ...db.session import get_db

router = APIRouter()
logger = logging.getLogger("dream-os.stream")


class ChatRequest(BaseModel):
    message: str
    model: Optional[str] = "agnes-2.0-flash"
    mode: Optional[str] = "chat"
    conversation_id: Optional[str] = ""


# 图片生成关键词检测
IMAGE_KEYWORDS = ["画", "生成图片", "图片", "照片", "壁纸", "头像", "插图", "插画", "海报", "封面", "艺术照"]


def _sse(event_type: str, data: dict) -> str:
    payload = json.dumps(data, ensure_ascii=False)
    return f"data: {payload}\n\n"


@router.post("/api/chat/stream")
async def chat_stream(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    mode = request.mode or "chat"
    conversation_id = request.conversation_id or str(uuid.uuid4())[:8]
    msg_lower = request.message.lower()

    # ── 图片生成强制路由 ──
    if any(k in msg_lower for k in IMAGE_KEYWORDS):
        logger.info(f"Image generation forced routing: {request.message[:50]}")

        async def image_event_generator():
            yield _sse("pipeline_start", {"type": "pipeline_start", "mode": "image"})
            yield _sse("intent", {"type": "intent", "intent": "image", "confidence": 0.95})
            yield _sse("tool_start", {
                "type": "tool_start",
                "tool": "image_generate",
                "description": request.message[:100],
            })

            try:
                tool = ImageTool()
                result = await tool.execute(command=f"image:{request.message}")

                if result.success:
                    data = json.loads(result.stdout)
                    image_url = data.get("image_url", "")
                    yield _sse("tool_result", {
                        "type": "tool_result",
                        "tool": "image_generate",
                        "success": True,
                        "output": json.dumps({"image_url": image_url}, ensure_ascii=False),
                    })
                    yield _sse("content", {
                        "type": "content",
                        "content": f"已为您生成图片：\n\n![生成图片]({image_url})",
                    })
                else:
                    yield _sse("tool_result", {
                        "type": "tool_result",
                        "tool": "image_generate",
                        "success": False,
                        "output": result.stderr or "图片生成失败",
                    })
                    yield _sse("content", {
                        "type": "content",
                        "content": f"图片生成失败: {result.stderr or '未知错误'}",
                    })
            except Exception as e:
                logger.error(f"Image generation error: {e}")
                yield _sse("content", {
                    "type": "content",
                    "content": f"图片生成出错: {str(e)[:200]}",
                })

            yield _sse("done", {"type": "done"})

        return StreamingResponse(
            image_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ── 普通聊天 ──
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