"""设置 API — 存数据库，改完即时生效"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from ...db.session import get_db
from ...models.setting import Setting
from ...core.ai_provider import invalidate_cache

router = APIRouter(prefix="/api/settings", tags=["settings"])


class ModelSettings(BaseModel):
    base_url: str
    api_key: str
    model: str
    provider: str = "custom"


@router.get("/model")
async def get_model_settings(db: AsyncSession = Depends(get_db)):
    """获取当前模型配置"""
    keys = ["provider", "base_url", "api_key", "model"]
    settings = {}
    for key in keys:
        result = await db.execute(select(Setting).where(Setting.key == f"model_{key}"))
        row = result.scalar_one_or_none()
        settings[key] = row.value if row else ""
    return {"settings": settings}


@router.post("/model")
async def save_model_settings(req: ModelSettings, db: AsyncSession = Depends(get_db)):
    """保存模型配置 — 即时生效，无需重启"""
    mapping = {
        "provider": req.provider,
        "base_url": req.base_url,
        "api_key": req.api_key,
        "model": req.model,
    }
    for key, value in mapping.items():
        result = await db.execute(select(Setting).where(Setting.key == f"model_{key}"))
        row = result.scalar_one_or_none()
        if row:
            row.value = value
        else:
            db.add(Setting(key=f"model_{key}", value=value))
    await db.commit()

    # 清除 AI Provider 缓存，下次请求会重新读取
    invalidate_cache()

    return {"message": "模型配置已保存，即时生效"}


@router.post("/model/test")
async def test_model_connection(req: ModelSettings, db: AsyncSession = Depends(get_db)):
    """测试模型连接"""
    from openai import AsyncOpenAI

    client = AsyncOpenAI(
        api_key=req.api_key,
        base_url=req.base_url,
        timeout=15,
    )
    try:
        r = await client.chat.completions.create(
            model=req.model,
            messages=[{"role": "user", "content": "ping"}],
            max_tokens=5,
        )
        reply = r.choices[0].message.content or ""
        return {"ok": True, "reply": reply, "model": r.model}
    except Exception as e:
        return {"ok": False, "error": str(e)[:300]}
