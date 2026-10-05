"""Convert unmatched /api/ 404s to JSON envelope (06-api-conventions)."""

from __future__ import annotations

from django.http import JsonResponse

from api.exceptions import error_body


class ApiJson404Middleware:
    """Ensure /api/ 404s are JSON even when Django would render HTML (DEBUG).

    DRF view 404s already return the error envelope; this covers URL-resolution
    misses such as empty path params (``/api/quizzes//``).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/api/"):
            return response
        if response.status_code != 404:
            return response
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            return response
        return JsonResponse(
            error_body(code="not_found", message="Not found.", details={}),
            status=404,
        )
