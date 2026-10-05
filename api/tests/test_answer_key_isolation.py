"""X-KEY-ISOLATION — public take/browse paths never expose answer key."""

import pytest

from api.tests.helpers.factories import (
    assert_no_answer_key,
    make_attempt,
    make_quiz,
    make_user,
)


@pytest.mark.django_db
@pytest.mark.parametrize(
    "scenario",
    ["list", "retrieve", "start", "get_in_progress"],
)
def test_public_surfaces_omit_answer_key(api_client, scenario):
    """List, retrieve, start attempt, in-progress GET: no is_correct / explanation."""
    user = make_user()
    quiz = make_quiz(question_count=3)

    if scenario == "list":
        response = api_client.get("/api/quizzes/")
    elif scenario == "retrieve":
        response = api_client.get(f"/api/quizzes/{quiz.id}/")
    elif scenario == "start":
        response = api_client.post(
            f"/api/quizzes/{quiz.id}/attempts/",
            {"user_id": user.id},
            format="json",
        )
    else:
        attempt = make_attempt(user, quiz)
        response = api_client.get(f"/api/attempts/{attempt.attempt_key}/")

    assert response.status_code in {200, 201}
    assert_no_answer_key(response.json())
