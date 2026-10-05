"""IP-based fixed-window rate limit for /api/ — `.cursor/specs/06-api-conventions.md`."""

from __future__ import annotations

import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse


class ApiRateLimitMiddleware:
    """Enforce ``API_RATE_LIMIT_PER_MINUTE`` per IP over ``API_RATE_LIMIT_WINDOW_SECONDS``."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.path.startswith("/api/"):
            return self.get_response(request)
        # OpenAPI schema is under /api/ but should still be rate limited per spec
        # ("every route under /api/"). Keep it limited.

        limit = int(getattr(settings, "API_RATE_LIMIT_PER_MINUTE", 60))
        window = int(getattr(settings, "API_RATE_LIMIT_WINDOW_SECONDS", 60))
        if limit <= 0:
            return self.get_response(request)

        ip = self._client_ip(request)
        now = int(time.time())
        window_start = now - (now % window)
        reset_at = window_start + window
        cache_key = f"api-rl:{ip}:{window_start}"

        # Atomic-ish increment for locmem/redis backends
        try:
            count = cache.incr(cache_key)
        except ValueError:
            cache.add(cache_key, 0, timeout=window)
            try:
                count = cache.incr(cache_key)
            except ValueError:
                count = 1
                cache.set(cache_key, count, timeout=window)

        remaining = max(0, limit - count)
        if count > limit:
            retry_after = max(1, reset_at - now)
            response = JsonResponse(
                {
                    "error": {
                        "code": "rate_limit_exceeded",
                        "message": "Too many requests. Try again later.",
                        "details": {},
                    }
                },
                status=429,
            )
            response["Retry-After"] = str(retry_after)
            response["X-RateLimit-Limit"] = str(limit)
            response["X-RateLimit-Remaining"] = "0"
            response["X-RateLimit-Reset"] = str(reset_at)
            return response

        response = self.get_response(request)
        response["X-RateLimit-Limit"] = str(limit)
        response["X-RateLimit-Remaining"] = str(remaining)
        response["X-RateLimit-Reset"] = str(reset_at)
        return response

    @staticmethod
    def _client_ip(request) -> str:
        return request.META.get("REMOTE_ADDR") or "unknown"
