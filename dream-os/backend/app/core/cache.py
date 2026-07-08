"""缓存抽象层 — 架构优化版

统一缓存接口，支持：
- Redis 缓存（生产环境）
- 内存缓存（开发/降级）
- 自动降级（Redis 不可用时自动切到内存缓存）

使用方式完全兼容，原有代码无需修改。
"""
import time
import json
import logging
import asyncio
from typing import Optional, Any
from functools import wraps

logger = logging.getLogger("dream-os.cache")


class CacheBackend:
    """缓存后端基类"""

    async def get(self, key: str) -> Optional[str]:
        raise NotImplementedError

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError


class MemoryCache(CacheBackend):
    """内存缓存 — 基于 asyncio 的简单实现

    用于：
    - Redis 不可用时的降级
    - 开发环境
    - 单元测试
    """

    def __init__(self, max_size: int = 1000):
        self._data: dict[str, tuple[str, float]] = {}
        self._lock = asyncio.Lock()
        self._max_size = max_size

    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            value, expire_at = item
            if expire_at and time.time() > expire_at:
                del self._data[key]
                return None
            return value

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        async with self._lock:
            if len(self._data) >= self._max_size:
                self._evict_oldest()
            expire_at = time.time() + ttl if ttl > 0 else 0
            self._data[key] = (value, expire_at)
            return True

    async def delete(self, key: str) -> bool:
        async with self._lock:
            self._data.pop(key, None)
            return True

    async def exists(self, key: str) -> bool:
        return (await self.get(key)) is not None

    def _evict_oldest(self):
        """淘汰最旧的条目（简单的 FIFO 策略）"""
        if not self._data:
            return
        oldest_key = next(iter(self._data))
        del self._data[oldest_key]


class RedisCache(CacheBackend):
    """Redis 缓存后端"""

    def __init__(self, redis_client):
        self._redis = redis_client

    async def get(self, key: str) -> Optional[str]:
        return await self._redis.get(key)

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        await self._redis.set(key, value, ex=ttl)
        return True

    async def delete(self, key: str) -> bool:
        await self._redis.delete(key)
        return True

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(key) > 0


class CacheManager:
    """统一缓存管理器

    特性：
    - 自动选择后端（Redis 优先，内存降级）
    - 统一的 get/set/delete 接口
    - JSON 序列化支持
    - 缓存装饰器
    """

    def __init__(self):
        self._backend: Optional[CacheBackend] = None
        self._initialized = False
        self._init_lock = asyncio.Lock()

    async def _ensure_backend(self) -> CacheBackend:
        """确保后端已初始化（延迟初始化）"""
        if self._initialized:
            return self._backend

        async with self._init_lock:
            if self._initialized:
                return self._backend

            try:
                from ..db.session import get_redis
                redis = await get_redis()
                await redis.ping()
                self._backend = RedisCache(redis)
                logger.info("Cache backend: Redis")
            except Exception as e:
                logger.warning(f"Redis unavailable, falling back to memory cache: {e}")
                self._backend = MemoryCache()
                logger.info("Cache backend: Memory (fallback)")

            self._initialized = True
            return self._backend

    async def get(self, key: str) -> Optional[str]:
        backend = await self._ensure_backend()
        return await backend.get(key)

    async def set(self, key: str, value: str, ttl: int = 300) -> bool:
        backend = await self._ensure_backend()
        return await backend.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        backend = await self._ensure_backend()
        return await backend.delete(key)

    async def exists(self, key: str) -> bool:
        backend = await self._ensure_backend()
        return await backend.exists(key)

    async def get_json(self, key: str) -> Optional[Any]:
        """获取 JSON 格式缓存"""
        value = await self.get(key)
        if value:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return None
        return None

    async def set_json(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置 JSON 格式缓存"""
        return await self.set(key, json.dumps(value, ensure_ascii=False), ttl)

    def cached(self, ttl: int = 300, key_prefix: str = "cache"):
        """缓存装饰器 — 用于缓存异步函数结果

        用法:
            @cache.cached(ttl=300, key_prefix="user")
            async def get_user(user_id: int):
                ...
        """
        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                key_parts = [key_prefix, func.__name__]
                for a in args:
                    key_parts.append(str(a))
                for k, v in sorted(kwargs.items()):
                    key_parts.append(f"{k}={v}")
                cache_key = ":".join(key_parts)

                cached_result = await self.get_json(cache_key)
                if cached_result is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_result

                result = await func(*args, **kwargs)
                await self.set_json(cache_key, result, ttl)
                return result
            return wrapper
        return decorator


# 全局单例
cache_manager = CacheManager()


# 便捷函数
async def cache_get(key: str) -> Optional[str]:
    return await cache_manager.get(key)


async def cache_set(key: str, value: str, ttl: int = 300) -> bool:
    return await cache_manager.set(key, value, ttl)


async def cache_delete(key: str) -> bool:
    return await cache_manager.delete(key)


async def cache_get_json(key: str) -> Optional[Any]:
    return await cache_manager.get_json(key)


async def cache_set_json(key: str, value: Any, ttl: int = 300) -> bool:
    return await cache_manager.set_json(key, value, ttl)
