"""Shared fixtures for Quiz App API tests (catalog 08)."""

import pytest
from rest_framework.test import APIClient


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture(autouse=True)
def _high_rate_limit_for_domain_tests(settings):
    """Domain/HTTP tests must not trip 429 unless they opt into a low limit.

    Spec: 06-api-conventions / 08-test-catalog — raise or disable for business tests.
    """
    settings.API_RATE_LIMIT_PER_MINUTE = 10_000
    settings.API_RATE_LIMIT_WINDOW_SECONDS = 60


@pytest.fixture
def low_rate_limit(settings):
    """Use in rate-limit tests to force 429 quickly."""
    settings.API_RATE_LIMIT_PER_MINUTE = 3
    settings.API_RATE_LIMIT_WINDOW_SECONDS = 60
