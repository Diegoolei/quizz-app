"""X-RL-* — rate limiting on read/write; worker exempt (06 / catalog 08)."""

import pytest

from api.tests.helpers.factories import assert_error_envelope, make_user


@pytest.mark.django_db
def test_rate_limit_read_429(api_client, low_rate_limit):
    """GET exceeding limit → 429 rate_limit_exceeded + Retry-After."""
    user = make_user()
    for _ in range(3):
        api_client.get(f"/api/users/{user.id}/")
    response = api_client.get(f"/api/users/{user.id}/")
    assert response.status_code == 429
    assert_error_envelope(response.json(), code="rate_limit_exceeded")
    assert "Retry-After" in response.headers


@pytest.mark.django_db
def test_rate_limit_write_429(api_client, low_rate_limit):
    """POST exceeding limit → 429."""
    for i in range(3):
        api_client.post(
            "/api/users/",
            {"name": f"N{i}", "email": f"n{i}@example.com"},
            format="json",
        )
    response = api_client.post(
        "/api/users/",
        {"name": "Over", "email": "over-rl@example.com"},
        format="json",
    )
    assert response.status_code == 429
    assert_error_envelope(response.json(), code="rate_limit_exceeded")


@pytest.mark.django_db
def test_outbox_worker_not_rate_limited(low_rate_limit):
    """process_outbox management path is not HTTP rate limited."""
    from outbox.services.outbox_service import process_outbox
    from api.tests.helpers.factories import (
        complete_attempt,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=2)
    for _ in range(5):
        attempt = make_attempt(user, quiz)
        complete_attempt(attempt)

    # Must run without raising a rate-limit error even with low HTTP limit.
    process_outbox(limit=100)
