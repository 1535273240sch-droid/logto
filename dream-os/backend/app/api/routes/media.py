"""Media API 路由 — 图片生成、上传、列表"""
import os
import shutil
import uuid
import logging
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from openai import AsyncOpenAI
from ...db.session import get_db, async_session_factory
from ...models.media import Media
from ...config import get_settings

logger = logging.getLogger("dream-os")

router = APIRouter(prefix="/api/media", tags=["media"])

# Media storage directory
MEDIA_DIR = "/workspace/media"
os.makedirs(MEDIA_DIR, exist_ok=True)


class ImageGenerateRequest(BaseModel):
    prompt: str
    model: str = "agnes-image-2.0-flash"
    size: str = "1024x1024"
    n: int = 1


async def _get_image_client():
    """获取图片生成专用客户端 — 使用内置 Agnes 模型，与对话模型独立"""
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        base_url=settings.openai_base_url.rstrip("/"),
        timeout=60.0,
    )


@router.post("/generate/image")
async def generate_image(req: ImageGenerateRequest):
    """生成图片 — 使用内置 Agnes 图片模型"""
    try:
        client = await _get_image_client()
        response = await client.images.generate(
            model=req.model,
            prompt=req.prompt,
            n=req.n,
            size=req.size,
        )

        # Save to database
        results = []
        async with async_session_factory() as db:
            for img in response.data:
                media = Media(
                    type="image",
                    source="generated",
                    prompt=req.prompt,
                    model=req.model,
                    url=img.url or "",
                )
                # Parse size
                if req.size:
                    parts = req.size.split("x")
                    if len(parts) == 2:
                        media.width = int(parts[0])
                        media.height = int(parts[1])
                db.add(media)
                results.append({
                    "id": media.id,
                    "url": img.url or "",
                    "prompt": req.prompt,
                    "model": req.model,
                })
            await db.commit()

        return {"status": "ok", "images": results}

    except Exception as e:
        logger.exception(f"Image generation failed: {e}")
        raise HTTPException(500, detail=str(e))


@router.post("/upload")
async def upload_media(file: UploadFile = File(...)):
    """上传图片/视频"""
    try:
        allowed_types = ["image/png", "image/jpeg", "image/gif", "image/webp", "video/mp4", "video/webm"]
        if file.content_type not in allowed_types:
            raise HTTPException(400, detail=f"Unsupported file type: {file.content_type}")

        media_type = "video" if file.content_type.startswith("video") else "image"

        ext = file.filename.split(".")[-1] if file.filename else "png"
        file_id = str(uuid.uuid4())
        filename = f"{file_id}.{ext}"
        file_path = os.path.join(MEDIA_DIR, filename)

        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        url = f"/media/{filename}"

        async with async_session_factory() as db:
            media = Media(
                type=media_type,
                source="uploaded",
                url=url,
                local_path=file_path,
            )
            db.add(media)
            await db.commit()
            await db.refresh(media)

        return {
            "status": "ok",
            "media": {
                "id": media.id,
                "type": media_type,
                "url": url,
                "source": "uploaded",
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, detail=str(e))


@router.get("/list")
async def list_media(limit: int = 50, type: str = None):
    """获取媒体列表"""
    async with async_session_factory() as db:
        query = select(Media).order_by(Media.created_at.desc()).limit(limit)
        if type:
            query = query.where(Media.type == type)
        result = await db.execute(query)
        medias = result.scalars().all()
        return [
            {
                "id": m.id,
                "type": m.type,
                "source": m.source,
                "prompt": m.prompt,
                "model": m.model,
                "url": m.url,
                "created_at": str(m.created_at),
            }
            for m in medias
        ]


@router.delete("/{media_id}")
async def delete_media(media_id: str):
    """删除媒体"""
    async with async_session_factory() as db:
        result = await db.execute(select(Media).where(Media.id == media_id))
        media = result.scalar_one_or_none()
        if not media:
            raise HTTPException(404, detail="Media not found")

        if media.local_path and os.path.exists(media.local_path):
            os.remove(media.local_path)

        await db.delete(media)
        await db.commit()
        return {"status": "ok", "deleted": media_id}
