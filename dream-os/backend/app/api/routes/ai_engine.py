"""AI Engine 路由 — 前端模型管理卡片对接"""
import json
from fastapi import APIRouter, Depends, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from typing import Optional, List
from ...db.session import get_db
from ...models.setting import Setting
from ...core.ai_provider import invalidate_cache

router = APIRouter(prefix="/api/ai-engine", tags=["ai-engine"])


class ProviderItem(BaseModel):
    name: str = ""
    apiKey: str = ""
    baseUrl: str = ""
    modelId: str = ""
    isDefault: bool = False
    enabled: bool = False
    status: str = "disconnected"
    latencyMs: Optional[int] = None
    lastTested: Optional[str] = None
    id: Optional[str] = None
    createdAt: Optional[str] = None
    updatedAt: Optional[str] = None


class ProvidersRequest(BaseModel):
    providers: List[ProviderItem] = []


@router.get("/providers")
async def list_providers(db: AsyncSession = Depends(get_db)):
    """获取所有已保存的模型提供商"""
    result = await db.execute(
        select(Setting).where(Setting.key == "ai_engine_providers")
    )
    row = result.scalar_one_or_none()
    if row and row.value:
        try:
            providers = json.loads(row.value)
            return {"providers": providers}
        except Exception:
            pass
    return {"providers": []}


@router.post("/providers")
async def save_providers(req: ProvidersRequest, db: AsyncSession = Depends(get_db)):
    """保存所有模型提供商配置"""
    providers_data = [p.model_dump() for p in req.providers]

    # 存到数据库
    result = await db.execute(
        select(Setting).where(Setting.key == "ai_engine_providers")
    )
    row = result.scalar_one_or_none()
    if row:
        row.value = json.dumps(providers_data)
    else:
        db.add(Setting(key="ai_engine_providers", value=json.dumps(providers_data)))
    await db.commit()

    # 找到默认且启用的 provider，更新 model_* 配置
    for p in req.providers:
        if p.isDefault and p.enabled and p.apiKey:
            mapping = {
                "model_provider": p.name,
                "model_base_url": p.baseUrl,
                "model_api_key": p.apiKey,
                "model_model": p.modelId,
            }
            for key, value in mapping.items():
                r = await db.execute(
                    select(Setting).where(Setting.key == key)
                )
                r2 = r.scalar_one_or_none()
                if r2:
                    r2.value = value
                else:
                    db.add(Setting(key=key, value=value))
            await db.commit()
            invalidate_cache()
            break

    return {"ok": True, "count": len(req.providers)}
