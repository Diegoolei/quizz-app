"""HTTP quizzes — catalog Q-* (http/quizzes.md)."""

import pytest

from api.tests.helpers.factories import (
    assert_error_envelope,
    assert_no_answer_key,
    make_quiz,
    quiz_create_payload,
)


@pytest.mark.django_db
def test_list_quizzes_200_omits_answer_key(api_client):
    """GET /api/quizzes/ → 200 summaries; no is_correct / explanation."""
    make_quiz(question_count=5, title="Intro to LLMs")
    response = api_client.get("/api/quizzes/")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)
    assert body[0]["title"] == "Intro to LLMs"
    assert "question_count" in body[0]
    assert_no_answer_key(body)


@pytest.mark.django_db
def test_retrieve_quiz_200_public_shape(api_client):
    """GET /api/quizzes/{id}/ → questions/options without is_correct or explanation."""
    quiz = make_quiz(question_count=5)
    response = api_client.get(f"/api/quizzes/{quiz.id}/")
    assert response.status_code == 200
    body = response.json()
    assert len(body["questions"]) == 5
    assert_no_answer_key(body)


@pytest.mark.django_db
def test_retrieve_quiz_404(api_client):
    """Unknown quiz → 404 quiz_not_found."""
    response = api_client.get("/api/quizzes/999999/")
    assert response.status_code == 404
    assert_error_envelope(response.json(), code="quiz_not_found")


@pytest.mark.django_db
def test_create_quiz_201_includes_answer_key(api_client):
    """POST /api/quizzes/ authoring → 201; response may include is_correct + explanation."""
    payload = quiz_create_payload(question_count=5)
    response = api_client.post("/api/quizzes/", payload, format="json")
    assert response.status_code == 201
    body = response.json()
    assert body["questions"][0]["explanation"]
    assert any(o["is_correct"] for o in body["questions"][0]["options"])


@pytest.mark.django_db
def test_create_quiz_422_no_questions(api_client):
    """No questions → 422 validation_error."""
    response = api_client.post(
        "/api/quizzes/",
        {"title": "Empty", "description": "", "questions": []},
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


@pytest.mark.django_db
def test_create_quiz_422_one_option(api_client):
    """<2 options → 422."""
    response = api_client.post(
        "/api/quizzes/",
        {
            "title": "Bad",
            "questions": [
                {
                    "text": "Q?",
                    "explanation": "E",
                    "position": 1,
                    "options": [{"text": "Only", "is_correct": True, "position": 1}],
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")


@pytest.mark.django_db
def test_create_quiz_422_zero_correct(api_client):
    """≠1 correct option → 422."""
    response = api_client.post(
        "/api/quizzes/",
        {
            "title": "Bad",
            "questions": [
                {
                    "text": "Q?",
                    "explanation": "E",
                    "position": 1,
                    "options": [
                        {"text": "A", "is_correct": False, "position": 1},
                        {"text": "B", "is_correct": False, "position": 2},
                    ],
                }
            ],
        },
        format="json",
    )
    assert response.status_code == 422
    assert_error_envelope(response.json(), code="validation_error")
