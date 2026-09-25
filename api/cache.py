"""Response caching: an in-process TTL cache keyed on path+query, plus Cache-Control so Cloudflare's edge caches too."""

from __future__ import annotations

from collections.abc import Callable
from functools import wraps
from typing import Any

from cachetools import TTLCache
from fastapi import Request, Response

from api.config import get_settings

_cache: TTLCache | None = None


def cache() -> TTLCache:
    global _cache
    if _cache is None:
        _cache = TTLCache(maxsize=2048, ttl=get_settings().cache_ttl_s)
    return _cache


def cached(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Memoise a GET handler on its full URL; handlers must take `request: Request` and `response: Response`."""

    @wraps(fn)
    async def wrapper(request: Request, response: Response, *args: Any, **kwargs: Any) -> Any:
        key = str(request.url)
        ttl = get_settings().cache_ttl_s
        response.headers["Cache-Control"] = f"public, max-age={ttl}, stale-while-revalidate={ttl * 3}"
        hit = cache().get(key)
        if hit is not None:
            return hit
        value = await fn(request, response, *args, **kwargs)
        cache()[key] = value
        return value

    return wrapper
