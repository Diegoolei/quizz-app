"""HTTP user progress — catalog P-* (http/user-progress.md)."""

import pytest

from api.tests.helpers.factories import (
    assert_error_envelope,
    complete_attempt,
    make_attempt,
    make_quiz,
    make_user,
)


@pytest.mark.django_db
def test_list_attempts_includes_retakes_and_null_score(api_client):
    """GET /api/users/{id}/attempts/ — retakes as rows; score_percent null if in_progress."""
    user = make_user()
    quiz = make_quiz(question_count=2)
    first = make_attempt(user, quiz)
    complete_attempt(first)
    abandoned = make_attempt(user, quiz)

    response = api_client.get(f"/api/users/{user.id}/attempts/")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    # newest first
    assert body[0]["attempt_key"] == abandoned.attempt_key
    assert body[0]["score_percent"] is None
    assert body[1]["score_percent"] is not None


@pytest.mark.django_db
def test_list_attempts_404(api_client):
    """Unknown user → 404 user_not_found."""
    response = api_client.get("/api/users/999999/attempts/")
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="user_not_found")


@pytest.mark.django_db
def test_stats_average_ignores_abandoned(api_client):
    """Stats average_score_percent uses completed only; abandoned excluded."""
    user = make_user()
    quiz = make_quiz(question_count=2)
    a1 = make_attempt(user, quiz)
    complete_attempt(a1)  # 100%
    make_attempt(user, quiz)  # abandoned

    # Second completed at 0%: all wrong
    from quizzes.models import Option, Question

    a2 = make_attempt(user, quiz)
    wrong_answers = []
    for question in Question.objects.filter(quiz=quiz).order_by("position"):
        wrong = Option.objects.get(question=question, is_correct=False)
        wrong_answers.append({"question_id": question.id, "option_id": wrong.id})
    complete_attempt(a2, answers=wrong_answers)

    response = api_client.get(f"/api/users/{user.id}/stats/")
    assert response.status_code == 200
    body = response.json()
    assert body["total_attempts"] == 3
    assert body["completed_attempts"] == 2
    assert body["abandoned_attempts"] == 1
    quiz_stats = next(q for q in body["quizzes"] if q["quiz_id"] == quiz.id)
    assert quiz_stats["completed_attempts"] == 2
    assert quiz_stats["abandoned_attempts"] == 1
    assert quiz_stats["average_score_percent"] == 50  # (100+0)/2


@pytest.mark.django_db
def test_stats_null_average_when_only_abandoned(api_client):
    """Only abandoned attempts for a quiz → average_score_percent null."""
    user = make_user()
    quiz = make_quiz(question_count=2)
    make_attempt(user, quiz)

    response = api_client.get(f"/api/users/{user.id}/stats/")
    assert response.status_code == 200
    quiz_stats = response.json()["quizzes"][0]
    assert quiz_stats["average_score_percent"] is None


@pytest.mark.django_db
def test_stats_404(api_client):
    """Unknown user → 404."""
    response = api_client.get("/api/users/999999/stats/")
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="user_not_found")
