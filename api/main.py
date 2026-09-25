"""FastAPI entry point: GET-only, cached, rate-limited, CORS-locked to the site. Jobs never run here."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.config import get_settings
from api.ratelimit import limiter
from api.routers import meta

logging.basicConfig(level=get_settings().log_level)

app = FastAPI(
    title="commanders",
    version="0.1.0",
    summary="Washington Commanders front-office analytics (read-only)",
    default_response_class=ORJSONResponse,
)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().origins(),
    allow_methods=["GET", "HEAD"],
    allow_headers=["*"],
)
app.include_router(meta.router)


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(request, exc):  # noqa: ANN001
    return ORJSONResponse({"detail": "rate limit exceeded"}, status_code=429)
