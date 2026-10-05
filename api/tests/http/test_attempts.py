"""HTTP attempts — catalog A-* (http/attempts.md)."""

import pytest

from api.tests.helpers.factories import (
    all_correct_answers_payload,
    assert_error_envelope,
    assert_no_answer_key,
    make_attempt,
    make_quiz,
    make_user,
)


@pytest.mark.django_db
def test_start_attempt_201_omits_answer_key(api_client):
    """POST /api/quizzes/{id}/attempts/ → 201 attempt_key + questions without answer key."""
    user = make_user()
    quiz = make_quiz(question_count=5)
    response = api_client.post(
        f"/api/quizzes/{quiz.id}/attempts/",
        {"user_id": user.id},
        format="json",
    )
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "in_progress"
    assert body["attempt_key"]
    assert len(body["questions"]) == 5
    assert_no_answer_key(body)


@pytest.mark.django_db
def test_start_attempt_404_quiz(api_client):
    """Unknown quiz → 404 quiz_not_found."""
    user = make_user()
    response = api_client.post(
        "/api/quizzes/999999/attempts/",
        {"user_id": user.id},
        format="json",
    )
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="quiz_not_found")


@pytest.mark.django_db
def test_start_attempt_404_user(api_client):
    """Unknown user → 404 user_not_found."""
    quiz = make_quiz(question_count=2)
    response = api_client.post(
        f"/api/quizzes/{quiz.id}/attempts/",
        {"user_id": 999999},
        format="json",
    )
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="user_not_found")


@pytest.mark.django_db
def test_start_attempt_422_missing_user(api_client):
    """Missing user_id → 422 validation_error."""
    quiz = make_quiz(question_count=2)
    response = api_client.post(
        f"/api/quizzes/{quiz.id}/attempts/",
        {},
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


@pytest.mark.django_db
def test_submit_answers_200_save_only(api_client):
    """POST answers → 200 {saved:true, status:completed}; no score/breakdown."""
    user = make_user()
    quiz = make_quiz(question_count=5)
    attempt = make_attempt(user, quiz)
    response = api_client.post(
        f"/api/attempts/{attempt.attempt_key}/answers/",
        all_correct_answers_payload(quiz),
        format="json",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["saved"] is True
    assert body["status"] == "completed"
    assert "score_percent" not in body
    assert "breakdown" not in body
    assert "performance_message" not in body

    from outbox.models import OutboxEvent

    assert OutboxEvent.objects.filter(
        uniqueness_key=f"attempt_completed:{attempt.id}",
        status="pending",
    ).exists()


@pytest.mark.django_db
def test_submit_incomplete_422(api_client):
    """Incomplete answers → 422 incomplete_answers; attempt stays in_progress."""
    user = make_user()
    quiz = make_quiz(question_count=3)
    attempt = make_attempt(user, quiz)
    response = api_client.post(
        f"/api/attempts/{attempt.attempt_key}/answers/",
        {"answers": []},
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="incomplete_answers")
    attempt.refresh_from_db()
    assert attempt.status == "in_progress"


@pytest.mark.django_db
def test_submit_double_409(api_client):
    """Second submit → 409 attempt_already_completed."""
    user = make_user()
    quiz = make_quiz(question_count=2)
    attempt = make_attempt(user, quiz)
    payload = all_correct_answers_payload(quiz)
    assert (
        api_client.post(
            f"/api/attempts/{attempt.attempt_key}/answers/",
            payload,
            format="json",
        ).status_code
        == 200
    )
    response = api_client.post(
        f"/api/attempts/{attempt.attempt_key}/answers/",
        payload,
        format="json",
    )
    assert response.status_code == 409
    assert_error_envelope(response.json(), code="attempt_already_completed")


@pytest.mark.django_db
def test_submit_404(api_client):
    """Unknown attempt_key → 404 attempt_not_found."""
    response = api_client.post(
        "/api/attempts/00000000-0000-0000-0000-000000000000/answers/",
        {"answers": []},
        format="json",
    )
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="attempt_not_found")


@pytest.mark.django_db
def test_get_attempt_in_progress(api_client):
    """GET in_progress → no score values; no answer key."""
    user = make_user()
    quiz = make_quiz(question_count=3)
    attempt = make_attempt(user, quiz)
    response = api_client.get(f"/api/attempts/{attempt.attempt_key}/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "in_progress"
    assert body.get("completed_at") is None
    assert_no_answer_key(body)


@pytest.mark.django_db
def test_get_attempt_completed_results(api_client):
    """GET completed → score, breakdown, performance_message, notification_status."""
    user = make_user()
    quiz = make_quiz(question_count=5)
    attempt = make_attempt(user, quiz)
    assert (
        api_client.post(
            f"/api/attempts/{attempt.attempt_key}/answers/",
            all_correct_answers_payload(quiz),
            format="json",
        ).status_code
        == 200
    )
    response = api_client.get(f"/api/attempts/{attempt.attempt_key}/")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["correct_count"] == 5
    assert body["total_count"] == 5
    assert body["score_percent"] == 100
    assert body["performance_message"] == "Excellent"
    assert body["notification_status"] == "pending"
    assert len(body["breakdown"]) == 5
    assert "explanation" in body["breakdown"][0]
    assert "correct_option_id" in body["breakdown"][0]


@pytest.mark.django_db
def test_get_attempt_404(api_client):
    """Unknown key → 404 attempt_not_found."""
    response = api_client.get(
        "/api/attempts/00000000-0000-0000-0000-000000000000/"
    )
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="attempt_not_found")
