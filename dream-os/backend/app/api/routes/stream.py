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
from ...tools.weather import WeatherTool
from ...tools.stock import StockTool
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

# 天气查询关键词检测
WEATHER_KEYWORDS = ["天气", "温度", "多少度", "热不热", "冷不冷", "下雨", "下雪", "刮风", "台风", "空气质量", "雾霾", "湿度"]

# 股票查询关键词检测
STOCK_KEYWORDS = ["股票", "股价", "行情", "涨了", "跌了", "基金", "黄金", "金价", "比特币", "加密货币", "美股", "A股", "港股"]


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

    # ── 天气查询强制路由 ──
    weather_keywords_in_msg = [k for k in WEATHER_KEYWORDS if k in msg_lower]
    if weather_keywords_in_msg:
        logger.info(f"Weather query forced routing: {request.message[:50]}")

        async def weather_event_generator():
            yield _sse("pipeline_start", {"type": "pipeline_start", "mode": "weather"})
            yield _sse("intent", {"type": "intent", "intent": "weather", "confidence": 0.9})

            # 从消息中提取城市名（取"天气/温度"前面的词）
            import re
            city = "深圳"
            for pattern in [r"(.+?)天气", r"(.+?)温度", r"(.+?)多少度", r"(.+?)下雨"]:
                m = re.search(pattern, request.message)
                if m:
                    candidate = m.group(1).strip()
                    if candidate and candidate not in ["今天", "明天", "后天", "昨天", "现在", "请问"]:
                        city = candidate
                        break

            command = f"weather:{city}"
            yield _sse("tool_start", {"type": "tool_start", "tool": "weather_query", "description": command})

            try:
                tool = WeatherTool()
                result = await tool.execute(command=command)
                if result.success:
                    data = json.loads(result.stdout)
                    weather_text = (
                        f"🌍 {data.get('city', city)} {data.get('country', '')}\n"
                        f"🌡 温度: {data['temp_C']}°C (体感 {data['feels_like_C']}°C)\n"
                        f"☁ 天气: {data['weather_desc']}\n"
                        f"💧 湿度: {data['humidity']}%\n"
                        f"🌬 风速: {data['wind_speed_kmh']}km/h {data['wind_dir']}\n"
                        f"👁 能见度: {data['visibility_km']}km\n"
                        f"📊 气压: {data['pressure_mb']}mb"
                    )
                    yield _sse("tool_result", {"type": "tool_result", "tool": "weather_query", "success": True, "output": json.dumps(data, ensure_ascii=False)})
                    yield _sse("content", {"type": "content", "content": weather_text})
                else:
                    yield _sse("tool_result", {"type": "tool_result", "tool": "weather_query", "success": False, "output": result.stderr or "查询失败"})
                    yield _sse("content", {"type": "content", "content": f"天气查询失败: {result.stderr}"})
            except Exception as e:
                logger.error(f"Weather query error: {e}")
                yield _sse("content", {"type": "content", "content": f"天气查询出错: {str(e)[:200]}"})

            yield _sse("done", {"type": "done"})

        return StreamingResponse(
            weather_event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    # ── 股票查询强制路由 ──
    stock_keywords_in_msg = [k for k in STOCK_KEYWORDS if k in msg_lower]
    if stock_keywords_in_msg:
        logger.info(f"Stock query forced routing: {request.message[:50]}")

        async def stock_event_generator():
            yield _sse("pipeline_start", {"type": "pipeline_start", "mode": "stock"})
            yield _sse("intent", {"type": "intent", "intent": "stock", "confidence": 0.9})

            # 提取股票代码或名称
            command = f"stock:{request.message}"
            yield _sse("tool_start", {"type": "tool_start", "tool": "stock_query", "description": command})

            try:
                tool = StockTool()
                result = await tool.execute(command=command)
                if result.success:
                    data = json.loads(result.stdout)
                    yield _sse("tool_result", {"type": "tool_result", "tool": "stock_query", "success": True, "output": result.stdout})
                    # 格式化输出
                    if "error" in data:
                        content_text = f"查询结果: {data['error']}"
                    else:
                        content_text = json.dumps(data, ensure_ascii=False, indent=2)
                    yield _sse("content", {"type": "content", "content": content_text})
                else:
                    yield _sse("tool_result", {"type": "tool_result", "tool": "stock_query", "success": False, "output": result.stderr or "查询失败"})
                    yield _sse("content", {"type": "content", "content": f"查询失败: {result.stderr}"})
            except Exception as e:
                logger.error(f"Stock query error: {e}")
                yield _sse("content", {"type": "content", "content": f"查询出错: {str(e)[:200]}"})

            yield _sse("done", {"type": "done"})

        return StreamingResponse(
            stock_event_generator(),
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