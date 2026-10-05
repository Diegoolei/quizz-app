"""D-ENV / D-ENV-EMPTY-PATH — error envelope shape (06-api-conventions)."""

import pytest

from api.tests.helpers.factories import assert_error_envelope


@pytest.mark.django_db
def test_404_uses_error_envelope(api_client):
    """Unknown resource → 404 with {error: {code, message, details}}."""
    response = api_client.get("/api/users/999999/")
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="user_not_found")


@pytest.mark.django_db
def test_422_uses_error_envelope(api_client):
    """Invalid create user → 422 validation_error envelope."""
    response = api_client.post("/api/users/", {"name": "", "email": "bad"}, format="json")
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


def test_empty_quiz_id_path_returns_json_not_found(api_client):
    """GET /api/quizzes// (empty id) → 404 JSON not_found; never HTML debug 404.

    Contract (06-api-conventions Unmatched /api/ routes):
    unmatched /api/ paths including empty path params MUST return
    {error: {code: not_found, message, details}} with Content-Type JSON.
    """
    response = api_client.get("/api/quizzes//")
    assert response.status_code == 404
    content_type = response.get("Content-Type", "")
    assert "application/json" in content_type
    body = response.json()
    assert_error_envelope(body, code="not_found")
    assert "<!DOCTYPE" not in response.content.decode("utf-8", errors="ignore")
    assert "Page not found" not in response.content.decode("utf-8", errors="ignore")
