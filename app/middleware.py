"""
VerifPay — Security Middleware

Provides:
    - API key authentication (X-API-Key header)
    - Rate limiting per IP via slowapi
"""

import logging

from fastapi import Request, HTTPException, Security
from fastapi.security import APIKeyHeader
from slowapi import Limiter
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings

logger = logging.getLogger(__name__)

# ─── Rate Limiter ──────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=[settings.RATE_LIMIT])

# ─── API Key Authentication ────────────────────────────────────

# Paths that don't require authentication
PUBLIC_PATHS = {
    "/", "/health", "/docs", "/redoc", "/openapi.json",
    "/webhook/telegram",  # Telegram sends updates here — must be open
}


class APIKeyMiddleware(BaseHTTPMiddleware):
    """
    Validates X-API-Key header on protected endpoints.
    If VERIFPAY_API_KEY is empty/unset, authentication is disabled (dev mode).
    """

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no API key is configured (development mode)
        if not settings.VERIFPAY_API_KEY:
            return await call_next(request)

        # Skip auth for public paths
        path = request.url.path.rstrip("/") or "/"
        if path in PUBLIC_PATHS:
            return await call_next(request)

        # Skip auth for OPTIONS (CORS preflight)
        if request.method == "OPTIONS":
            return await call_next(request)

        # Validate API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key != settings.VERIFPAY_API_KEY:
            logger.warning(f"Rejected request with invalid API key from {request.client.host}")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid or missing API key. Provide X-API-Key header."},
            )

        return await call_next(request)
