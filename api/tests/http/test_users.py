"""HTTP users — catalog U-* (http/users.md)."""

import pytest

from api.tests.helpers.factories import assert_error_envelope, make_user


@pytest.mark.django_db
def test_create_user_201(api_client):
    """POST /api/users/ → 201 {id, name, email}."""
    response = api_client.post(
        "/api/users/",
        {"name": "Ada Lovelace", "email": "ada@example.com"},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Ada Lovelace"
    assert body["email"] == "ada@example.com"
    assert "id" in body


@pytest.mark.django_db
def test_create_user_422_blank_name(api_client):
    """Blank name → 422 validation_error."""
    response = api_client.post(
        "/api/users/",
        {"name": "", "email": "x@example.com"},
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


@pytest.mark.django_db
def test_create_user_422_invalid_email(api_client):
    """Invalid email → 422 validation_error."""
    response = api_client.post(
        "/api/users/",
        {"name": "Ada", "email": "not-an-email"},
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


@pytest.mark.django_db
def test_create_user_409_duplicate_email(api_client):
    """Duplicate email → 409 email_taken."""
    make_user(email="dup@example.com")
    response = api_client.post(
        "/api/users/",
        {"name": "Other", "email": "dup@example.com"},
        format="json",
    )
    assert response.status_code == 409
    assert_error_envelope(response.json(), code="email_taken")


@pytest.mark.django_db
def test_create_user_400_invalid_json(api_client):
    """Malformed JSON → 400 invalid_json."""
    response = api_client.post(
        "/api/users/",
        b"{not-json",
        content_type="application/json",
    )
    assert response.status_code == 400
    assert_error_envelope(response.json(), code="invalid_json")


@pytest.mark.django_db
def test_get_user_200(api_client):
    """GET /api/users/{id}/ → 200."""
    user = make_user(name="Grace", email="grace@example.com")
    response = api_client.get(f"/api/users/{user.id}/")
    assert response.status_code == 200
    assert response.json()["email"] == "grace@example.com"


@pytest.mark.django_db
def test_get_user_404(api_client):
    """Unknown id → 404 user_not_found."""
    response = api_client.get("/api/users/999999/")
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="user_not_found")


@pytest.mark.django_db
def test_create_user_429(api_client, low_rate_limit):
    """Over rate limit → 429 rate_limit_exceeded + Retry-After."""
    for i in range(3):
        api_client.post(
            "/api/users/",
            {"name": f"U{i}", "email": f"u{i}@example.com"},
            format="json",
        )
    response = api_client.post(
        "/api/users/",
        {"name": "Over", "email": "over@example.com"},
        format="json",
    )
    assert response.status_code == 429
    assert_error_envelope(response.json(), code="rate_limit_exceeded")
    assert "Retry-After" in response.headers


@pytest.mark.django_db
def test_get_user_429(api_client, low_rate_limit):
    """GET over rate limit → 429."""
    user = make_user()
    for _ in range(3):
        api_client.get(f"/api/users/{user.id}/")
    response = api_client.get(f"/api/users/{user.id}/")
    assert response.status_code == 429
    assert_error_envelope(response.json(), code="rate_limit_exceeded")
