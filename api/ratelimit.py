"""Per-client rate limiting; behind the tunnel the client address is Cloudflare's CF-Connecting-IP header."""

from __future__ import annotations

from fastapi import Request
from slowapi import Limiter

from api.config import get_settings


def client_ip(request: Request) -> str:
    return request.headers.get("CF-Connecting-IP") or (request.client.host if request.client else "unknown")


limiter = Limiter(key_func=client_ip, default_limits=[get_settings().rate_limit])
