"""AI Provider 抽象层 - 统一 AI 接口，支持运行时切换模型"""
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator
import json
from openai import AsyncOpenAI
from ..config import get_settings


# 全局缓存
_cached_client: AsyncOpenAI | None = None
_cached_model: str | None = None
_cached_config_hash: str | None = None

# 复用已有的 async engine，避免每次创建新连接
_async_engine_ref = None


def invalidate_cache():
    """外部调用：保存设置后清缓存，下次请求重建"""
    global _cached_client, _cached_model, _cached_config_hash
    _cached_client = None
    _cached_model = None
    _cached_config_hash = None


async def _read_db_settings_async() -> dict:
    """异步方式读 DB，复用已有的 async engine，不阻塞事件循环"""
    global _async_engine_ref
    try:
        from sqlalchemy import text
        from ..db.session import engine as _engine
        # 复用全局 async engine，不再每次创建新 engine
        _async_engine_ref = _engine
        async with _engine.connect() as conn:
            result = await conn.execute(text(
                "SELECT key, value FROM settings WHERE key IN ('model_base_url','model_api_key','model_model')"
            ))
            rows = result.fetchall()
            return {r[0]: r[1] for r in rows}
    except Exception:
        return {}


async def get_ai_client() -> tuple[AsyncOpenAI, str]:
    """获取 AI 客户端，缓存优先"""
    global _cached_client, _cached_model, _cached_config_hash

    if _cached_client is not None and _cached_model is not None:
        return _cached_client, _cached_model

    # 读 DB（异步方式，复用已有连接池，不阻塞事件循环）
    db_settings = await _read_db_settings_async()

    env = get_settings()
    api_key = db_settings.get("model_api_key") or env.openai_api_key
    base_url = db_settings.get("model_base_url") or env.openai_base_url
    model = db_settings.get("model_model") or env.openai_model

    _cached_client = AsyncOpenAI(api_key=api_key, base_url=base_url)
    _cached_model = model
    return _cached_client, _cached_model


class AIProvider(ABC):
    @abstractmethod
    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict: ...
    @abstractmethod
    async def chat_stream(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncGenerator[str, None]: ...
    @abstractmethod
    async def plan(self, task: str, context: dict) -> list[dict]: ...


class OpenAICompatibleProvider(AIProvider):
    """OpenAI 兼容 Provider — 运行时缓存，切换模型后自动刷新"""

    @property
    def temperature(self) -> float:
        return get_settings().ai_temperature

    @property
    def max_tokens(self) -> int:
        return get_settings().ai_max_tokens

    async def chat(self, messages: list[dict], tools: list[dict] | None = None) -> dict:
        # 统一通过 async 接口获取 client 和 model，避免同步 DB 阻塞
        client, model = await get_ai_client()

        kwargs: dict[str, Any] = dict(
            model=model,
            messages=messages,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await client.chat.completions.create(**kwargs)
        choice = response.choices[0]
        result: dict[str, Any] = {"content": choice.message.content or "", "role": choice.message.role}
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {"id": tc.id, "name": tc.function.name, "arguments": json.loads(tc.function.arguments)}
                for tc in choice.message.tool_calls
            ]
        return result

    async def chat_stream(self, messages: list[dict], tools: list[dict] | None = None) -> AsyncGenerator[str, None]:
        client, model = await get_ai_client()

        kwargs: dict[str, Any] = dict(model=model, messages=messages, temperature=self.temperature, max_tokens=self.max_tokens, stream=True)
        if tools:
            kwargs["tools"] = tools
        stream = await client.chat.completions.create(**kwargs)
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content

    async def plan(self, task: str, context: dict) -> list[dict]:
        memory_str = json.dumps(context.get("memory", {}), ensure_ascii=False, indent=2)
        tools_str = json.dumps(context.get("tools", []), ensure_ascii=False)
        system_prompt = f"""你是 Dream OS 的 Task Planner。把用户任务拆解为可执行步骤。

可用工具: {tools_str}
服务器记忆: {memory_str}

规则:
1. 闲聊直接回复
2. 操作任务拆成具体步骤
3. 输出 JSON 数组

直接返回 JSON。"""

        client, model = await get_ai_client()
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"任务: {task}"},
            ],
            temperature=0.6,
            max_tokens=1024,
        )
        content = response.choices[0].message.content or "[]"
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(content)


_ai_provider: AIProvider | None = None


def get_ai_provider() -> AIProvider:
    global _ai_provider
    if _ai_provider is None:
        _ai_provider = OpenAICompatibleProvider()
    return _ai_provider
