"""AI Provider — 统一 LLM 客户端工厂（多 Provider 分层路由）"""
import json
import logging
import re
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from ..config import get_settings

logger = logging.getLogger("dream-os.ai_provider")

_cached_client = None
_cached_model = None
_cached_settings_hash = None

# 分层模型缓存
_tier_cache: dict[str, tuple] = {}


def invalidate_cache():
    global _cached_client, _cached_model, _cached_settings_hash
    _cached_client = None
    _cached_model = None
    _cached_settings_hash = None
    _tier_cache.clear()
    logger.info("AI Provider cache invalidated")


# 分层路由规则：tier -> 模型名匹配正则列表
TIER_PATTERNS = {
    "fast": [r"agnes", r"flash", r"air", r"turbo", r"glm"],
    "deep": [r"deepseek", r"deep", r"v3", r"r1", r"reasoner"],
}


async def _get_providers(db: AsyncSession) -> list[dict]:
    """从数据库读取所有 providers"""
    try:
        from ..models.setting import Setting
        result = await db.execute(
            select(Setting).where(Setting.key == "ai_engine_providers")
        )
        row = result.scalar_one_or_none()
        if row and row.value:
            return json.loads(row.value)
    except Exception as e:
        logger.warning(f"Failed to read ai_engine_providers: {e}")
    return []


def _match_tier(providers: list[dict], tier: str) -> Optional[dict]:
    """根据 tier 匹配最佳 provider"""
    patterns = TIER_PATTERNS.get(tier, [])
    model_lower = ""

    # 按优先级匹配
    for pattern in patterns:
        for p in providers:
            if not p.get("enabled") or not p.get("apiKey"):
                continue
            model_lower = (p.get("modelId", "") + p.get("name", "")).lower()
            if re.search(pattern, model_lower):
                logger.info(f"Tier '{tier}' matched provider: {p.get('name')} model={p.get('modelId')}")
                return p

    return None


def _pick_fallback(providers: list[dict]) -> Optional[dict]:
    """回退：默认 provider -> 第一个启用的"""
    for p in providers:
        if p.get("enabled") and p.get("apiKey") and p.get("isDefault"):
            return p
    for p in providers:
        if p.get("enabled") and p.get("apiKey"):
            return p
    return None


async def get_ai_client(db: Optional[AsyncSession] = None, tier: str = "fast"):
    """获取 AI 客户端和模型名

    支持分层路由:
    - tier="fast": Flash/Air/Agnes 模型（意图检测、路由、工具结果观察）
    - tier="deep": DeepSeek/V3 强模型（需求分析、架构设计、最终回复）
    """
    global _cached_client, _cached_model, _cached_settings_hash

    # 构建配置哈希
    settings_hash = "default"
    if db:
        providers = await _get_providers(db)
        if providers:
            settings_hash = json.dumps(providers)[:100]

    # 分层模型缓存
    cache_key = f"{settings_hash}:{tier}"
    if cache_key in _tier_cache:
        return _tier_cache[cache_key]

    api_key = ""
    base_url = ""
    model = "agnes-2.0-flash"

    if db:
        providers = await _get_providers(db)

        # 1. 按 tier 匹配
        matched = _match_tier(providers, tier)
        if matched:
            api_key = matched.get("apiKey", "")
            base_url = matched.get("baseUrl", "")
            model = matched.get("modelId", "gpt-4o")
            logger.info(f"Tier '{tier}' using: {matched.get('name')} model={model}")
        else:
            # 2. 回退
            fallback = _pick_fallback(providers)
            if fallback:
                api_key = fallback.get("apiKey", "")
                base_url = fallback.get("baseUrl", "")
                model = fallback.get("modelId", "gpt-4o")
                logger.info(f"Tier '{tier}' fallback to: {fallback.get('name')} model={model}")

    # 回退到旧 settings
    if not api_key and db:
        try:
            from ..models.setting import Setting
            for key in ["model_api_key", "model_base_url", "model"]:
                r = await db.execute(select(Setting).where(Setting.key == key))
                r2 = r.scalar_one_or_none()
                if r2:
                    if key == "model_api_key": api_key = r2.value
                    elif key == "model_base_url": base_url = r2.value
                    elif key == "model": model = r2.value
        except Exception:
            pass

    if not api_key or not base_url:
        logger.warning("No API key configured, AI will not work")
        raise ValueError("请先配置 AI 模型: 点击「AI 引擎」按钮添加 Provider")

    try:
        from openai import AsyncOpenAI
        client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=60,
        )
        if tier == "fast":
            _cached_client = client
            _cached_model = model
            _cached_settings_hash = settings_hash
        _tier_cache[cache_key] = (client, model)
        logger.info(f"AI client created: {base_url} model={model} tier={tier}")
        return client, model
    except Exception as e:
        logger.error(f"Failed to create AI client: {e}")
        raise
