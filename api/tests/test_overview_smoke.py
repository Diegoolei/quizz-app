"""X-SMOKE — end-to-end happy path (00-overview); run after units."""

import pytest

from api.tests.helpers.factories import assert_no_answer_key


@pytest.mark.django_db
def test_overview_happy_path(api_client):
    """Create user → list → start → submit save-only → results → stats; retake preserves history."""
    # Create user
    user_resp = api_client.post(
        "/api/users/",
        {"name": "Smoke Tester", "email": "smoke@example.com"},
        format="json",
    )
    assert user_resp.status_code == 201
    user_id = user_resp.json()["id"]

    # Ensure a quiz exists via create (authoring)
    quiz_resp = api_client.post(
        "/api/quizzes/",
        {
            "title": "Smoke Quiz",
            "description": "e2e",
            "questions": [
                {
                    "text": f"Q{i}?",
                    "explanation": f"E{i}",
                    "position": i,
                    "options": [
                        {"text": "Yes", "is_correct": True, "position": 1},
                        {"text": "No", "is_correct": False, "position": 2},
                    ],
                }
                for i in range(1, 6)
            ],
        },
        format="json",
    )
    assert quiz_resp.status_code == 201
    quiz_id = quiz_resp.json()["id"]

    list_resp = api_client.get("/api/quizzes/")
    assert list_resp.status_code == 200
    assert_no_answer_key(list_resp.json())

    start = api_client.post(
        f"/api/quizzes/{quiz_id}/attempts/",
        {"user_id": user_id},
        format="json",
    )
    assert start.status_code == 201
    assert_no_answer_key(start.json())
    attempt_key = start.json()["attempt_key"]
    questions = start.json()["questions"]

    answers = {
        "answers": [
            {
                "question_id": q["id"],
                "option_id": q["options"][0]["id"],
            }
            for q in questions
        ]
    }
    submit = api_client.post(
        f"/api/attempts/{attempt_key}/answers/",
        answers,
        format="json",
    )
    assert submit.status_code == 200
    assert submit.json()["saved"] is True
    assert "score_percent" not in submit.json()

    results = api_client.get(f"/api/attempts/{attempt_key}/")
    assert results.status_code == 200
    assert results.json()["score_percent"] == 100
    assert results.json()["notification_status"] == "pending"

    # Retake
    start2 = api_client.post(
        f"/api/quizzes/{quiz_id}/attempts/",
        {"user_id": user_id},
        format="json",
    )
    assert start2.status_code == 201
    assert start2.json()["attempt_key"] != attempt_key

    history = api_client.get(f"/api/users/{user_id}/attempts/")
    assert history.status_code == 200
    assert len(history.json()) == 2

    stats = api_client.get(f"/api/users/{user_id}/stats/")
    assert stats.status_code == 200
    assert stats.json()["completed_attempts"] == 1
    assert stats.json()["abandoned_attempts"] == 1
