"""OpenAPI schema view forced to JSON for clients/tests."""

from __future__ import annotations

from drf_spectacular.utils import extend_schema
from drf_spectacular.views import SpectacularAPIView
from rest_framework.renderers import JSONRenderer


@extend_schema(exclude=True)
class SpectacularJSONAPIView(SpectacularAPIView):
    """Schema endpoint itself is not part of the public http/*.md surface."""

    renderer_classes = [JSONRenderer]
