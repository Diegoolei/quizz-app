"""Test factories for domain entities (lazy model imports)."""

from __future__ import annotations

import uuid
from typing import Any


def make_user(**kwargs: Any):
    from users.models import User

    defaults = {
        "name": kwargs.pop("name", "Ada Lovelace"),
        "email": kwargs.pop("email", f"user-{uuid.uuid4().hex[:10]}@example.com"),
    }
    defaults.update(kwargs)
    return User.objects.create(**defaults)


def make_quiz(*, question_count: int = 5, options_per_question: int = 2, **kwargs: Any):
    """Create quiz with exactly one correct option per question."""
    from quizzes.models import Option, Question, Quiz

    title = kwargs.pop("title", f"Quiz {uuid.uuid4().hex[:8]}")
    description = kwargs.pop("description", "")
    quiz = Quiz.objects.create(title=title, description=description, **kwargs)

    if options_per_question < 2:
        raise ValueError("options_per_question must be >= 2")

    for q_pos in range(1, question_count + 1):
        question = Question.objects.create(
            quiz=quiz,
            text=f"Question {q_pos}?",
            explanation=f"Explanation for question {q_pos}.",
            position=q_pos,
        )
        for o_pos in range(1, options_per_question + 1):
            Option.objects.create(
                question=question,
                text=f"Option {o_pos}",
                is_correct=(o_pos == 1),
                position=o_pos,
            )
    return quiz


def make_attempt(user, quiz, *, status: str = "in_progress", **kwargs: Any):
    from attempts.models import Attempt

    defaults = {
        "user": user,
        "quiz": quiz,
        "status": status,
        "attempt_key": kwargs.pop("attempt_key", str(uuid.uuid4())),
    }
    defaults.update(kwargs)
    return Attempt.objects.create(**defaults)


def complete_attempt(attempt, *, answers: list[dict] | None = None):
    """Complete an attempt for setup when HTTP submit is not under test.

    ``answers``: optional list of {question_id, option_id}; default = all correct options.
    """
    from django.utils import timezone

    from attempts.models import AttemptAnswer
    from attempts.services.scoring import performance_message_for, score_percent
    from quizzes.models import Option, Question

    questions = list(
        Question.objects.filter(quiz_id=attempt.quiz_id).order_by("position")
    )
    if answers is None:
        answers = []
        for question in questions:
            correct = Option.objects.get(question=question, is_correct=True)
            answers.append(
                {"question_id": question.id, "option_id": correct.id}
            )

    correct_count = 0
    for row in answers:
        option = Option.objects.get(pk=row["option_id"])
        is_correct = option.is_correct
        if is_correct:
            correct_count += 1
        AttemptAnswer.objects.create(
            attempt=attempt,
            question_id=row["question_id"],
            option_id=row["option_id"],
            is_correct=is_correct,
        )

    total = len(questions)
    percent = score_percent(correct_count, total)
    attempt.status = "completed"
    attempt.completed_at = timezone.now()
    attempt.correct_count = correct_count
    attempt.total_count = total
    attempt.score_percent = percent
    attempt.performance_message = performance_message_for(percent)
    attempt.save()

    make_outbox_for_attempt(attempt, status="pending")
    return attempt


def make_outbox_for_attempt(attempt, *, status: str = "pending", **kwargs: Any):
    from outbox.models import OutboxEvent

    defaults = {
        "event_type": "quiz_attempt_completed",
        "status": status,
        "retries": 0,
        "uniqueness_key": f"attempt_completed:{attempt.id}",
        "payload": {
            "attempt_id": attempt.id,
            "user_name": attempt.user.name,
            "user_email": attempt.user.email,
            "quiz_title": attempt.quiz.title,
            "correct_count": attempt.correct_count,
            "total_count": attempt.total_count,
            "score_percent": attempt.score_percent,
            "performance_message": attempt.performance_message,
            "completed_at": (
                attempt.completed_at.isoformat() if attempt.completed_at else None
            ),
        },
    }
    defaults.update(kwargs)
    return OutboxEvent.objects.create(**defaults)


def quiz_create_payload(*, question_count: int = 5) -> dict:
    """Authoring body for POST /api/quizzes/."""
    questions = []
    for i in range(1, question_count + 1):
        questions.append(
            {
                "text": f"Q{i}?",
                "explanation": f"Because {i}.",
                "position": i,
                "options": [
                    {"text": "Correct", "is_correct": True, "position": 1},
                    {"text": "Wrong", "is_correct": False, "position": 2},
                ],
            }
        )
    return {
        "title": f"Created quiz {uuid.uuid4().hex[:8]}",
        "description": "test",
        "questions": questions,
    }


def all_correct_answers_payload(quiz) -> dict:
    from quizzes.models import Option, Question

    answers = []
    for question in Question.objects.filter(quiz=quiz).order_by("position"):
        opt = Option.objects.get(question=question, is_correct=True)
        answers.append({"question_id": question.id, "option_id": opt.id})
    return {"answers": answers}


def assert_no_answer_key(payload) -> None:
    """Fail if public JSON embeds answer-key fields anywhere."""
    forbidden = {"is_correct", "explanation", "correct_option_id"}
    if isinstance(payload, dict):
        overlap = forbidden & set(payload.keys())
        assert not overlap, f"answer-key fields present: {overlap}"
        for value in payload.values():
            assert_no_answer_key(value)
    elif isinstance(payload, list):
        for item in payload:
            assert_no_answer_key(item)


def assert_error_envelope(data: dict, *, code: str) -> None:
    assert "error" in data
    assert data["error"]["code"] == code
    assert "message" in data["error"]
    assert "details" in data["error"]
