"""D-ENV — error envelope shape (06-api-conventions)."""

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
