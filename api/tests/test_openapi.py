"""D-OAS — OpenAPI covers all /api/ paths including 429 (06-api-conventions)."""

import pytest

REQUIRED_PATHS = [
    "/api/users/",
    "/api/users/{id}/",
    "/api/quizzes/",
    "/api/quizzes/{id}/",
    "/api/quizzes/{quiz_id}/attempts/",
    "/api/attempts/{attempt_key}/answers/",
    "/api/attempts/{attempt_key}/",
    "/api/users/{user_id}/attempts/",
    "/api/users/{user_id}/stats/",
]


@pytest.mark.django_db
def test_openapi_schema_documents_paths_and_429(api_client):
    """Schema loads; every API path present; each operation documents 429."""
    response = api_client.get("/api/schema/")
    assert response.status_code == 200
    schema = response.json()
    paths = schema["paths"]

    # Allow either templating style
    def has_path(candidate: str) -> bool:
        if candidate in paths:
            return True
        # spectacular may use {id} vs {user_id}
        for key in paths:
            if key.replace("{id}", "{user_id}") == candidate:
                return True
            if key.replace("{id}", "{quiz_id}") == candidate:
                return True
        return candidate in paths

    for path in REQUIRED_PATHS:
        assert any(
            path == p
            or path.replace("{user_id}", "{id}") == p
            or path.replace("{quiz_id}", "{id}") == p
            for p in paths
        ), f"missing OpenAPI path for {path}; have {sorted(paths)}"

    for path, methods in paths.items():
        if not path.startswith("/api/"):
            continue
        for method, operation in methods.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            responses = operation.get("responses", {})
            assert "429" in responses, f"{method.upper()} {path} missing 429 response"
