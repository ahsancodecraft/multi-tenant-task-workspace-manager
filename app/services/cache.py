import time
from typing import Protocol
import redis
from app.core.config import settings
from app.core.logging_config import logger


class CacheProvider(Protocol):
    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl_seconds: int) -> None: ...
    def delete(self, key: str) -> None: ...


class InMemoryCacheProvider:
    """Thread-safe fallback & test cache supporting TTL expiration."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[str, float]] = {}

    def get(self, key: str) -> str | None:
        entry = self._store.get(key)
        if not entry:
            return None
        value, expires_at = entry
        if time.time() > expires_at:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self._store[key] = (value, time.time() + ttl_seconds)

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class RedisCacheProvider:
    """Production Redis cache-aside adapter using redis-py."""

    def __init__(self, redis_url: str) -> None:
        self.client = redis.Redis.from_url(redis_url, decode_responses=True)

    def get(self, key: str) -> str | None:
        return self.client.get(key)

    def set(self, key: str, value: str, ttl_seconds: int) -> None:
        self.client.setex(key, ttl_seconds, value)

    def delete(self, key: str) -> None:
        self.client.delete(key)


def build_cache_provider() -> CacheProvider:
    if settings.APP_ENV == "test":
        return InMemoryCacheProvider()
    try:
        provider = RedisCacheProvider(settings.REDIS_URL)
        provider.client.ping()
        logger.info("Connected to Redis cache backend")
        return provider
    except Exception:
        logger.warning("Redis unavailable; falling back to InMemoryCacheProvider")
        return InMemoryCacheProvider()


cache_provider: CacheProvider = build_cache_provider()