"""设置 API — 存数据库，改完即时生效"""
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional
from ...db.session import get_db
from ...models.setting import Setting
from ...core.ai_provider import invalidate_cache

router = APIRouter(prefix="/api", tags=["settings"])


class ModelSettings(BaseModel):
    base_url: str
    api_key: str
    model: str
    provider: str = "custom"


# ── 预设模型列表（前端模型选择器使用） ──────────────────────
_PRESET_MODELS = [
    {"name": "Agnes Flash", "model": "agnes-flash", "provider": "agnes"},
    {"name": "GPT-4o", "model": "gpt-4o", "provider": "openai"},
    {"name": "Claude 3.5 Sonnet", "model": "claude-3.5-sonnet", "provider": "anthropic"},
    {"name": "DeepSeek V3", "model": "deepseek-chat", "provider": "deepseek"},
    {"name": "GLM-4", "model": "glm-4", "provider": "zhipu"},
    {"name": "通义千问", "model": "qwen-plus", "provider": "aliyun"},
    {"name": "Doubao", "model": "doubao-pro", "provider": "doubao"},
    {"name": "Moonshot", "model": "moonshot-v1", "provider": "moonshot"},
    {"name": "Hunyuan", "model": "hunyuan-pro", "provider": "tencent"},
    {"name": "自定义", "model": "", "provider": "custom"},
]


@router.get("/models")
async def list_models(db: AsyncSession = Depends(get_db)):
    """返回预设模型列表 + 用户自定义模型"""
    # 读取用户已保存的模型配置
    result = await db.execute(select(Setting).where(Setting.key.like("saved_model_%")))
    saved_rows = result.scalars().all()
    custom_models = []
    for row in saved_rows:
        try:
            import json
            custom_models.append(json.loads(row.value))
        except Exception:
            pass
    return {"models": _PRESET_MODELS + custom_models}


@router.get("/settings/model")
async def get_model_settings(db: AsyncSession = Depends(get_db)):
    """获取当前模型配置"""
    keys = ["provider", "base_url", "api_key", "model"]
    settings = {}
    for key in keys:
        result = await db.execute(select(Setting).where(Setting.key == f"model_{key}"))
        row = result.scalar_one_or_none()
        settings[key] = row.value if row else ""
    return {"settings": settings}


@router.post("/settings/model")
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

    # 同时也保存到已保存模型列表
    import json
    saved = {"name": req.model, "model": req.model, "provider": req.provider, "base_url": req.base_url}
    result2 = await db.execute(select(Setting).where(Setting.key == f"saved_model_{req.provider}_{req.model}"))
    row2 = result2.scalar_one_or_none()
    if not row2:
        db.add(Setting(key=f"saved_model_{req.provider}_{req.model}", value=json.dumps(saved)))
        await db.commit()

    return {"message": "模型配置已保存，即时生效"}


@router.post("/settings/model/test")
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
