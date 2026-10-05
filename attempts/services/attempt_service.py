"""Attempt lifecycle services — specs 03 / 04 / 05 (enqueue on submit)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any
from uuid import UUID

from django.db import transaction
from django.db.models import Prefetch
from django.utils import timezone

from attempts.models import Attempt, AttemptAnswer
from attempts.services.exceptions import (
    AlreadyCompletedError,
    AttemptNotFound,
    IncompleteAnswersError,
    InvalidAnswerError,
)
from attempts.services.scoring import performance_message_for, score_percent
from outbox.services import enqueue_attempt_completed
from quizzes.models import Option, Question, Quiz
from quizzes.services.exceptions import QuizNotFound
from users.models import User
from users.services.exceptions import UserNotFound

# Re-export for test imports: ``from attempts.services.attempt_service import …``
__all__ = [
    "AlreadyCompletedError",
    "AttemptNotFound",
    "IncompleteAnswersError",
    "InvalidAnswerError",
    "get_attempt",
    "list_user_attempts",
    "start_attempt",
    "submit_answers",
    "user_stats",
]


def start_attempt(user_id: int, quiz_id: int) -> dict[str, Any]:
    """Create an in-progress attempt; return public quiz take shape (no answer key)."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist as exc:
        raise UserNotFound(details={"id": user_id}) from exc

    try:
        quiz = _load_quiz_with_public_questions(quiz_id)
    except Quiz.DoesNotExist as exc:
        raise QuizNotFound(details={"quiz_id": quiz_id}) from exc

    attempt = Attempt.objects.create(
        user=user,
        quiz=quiz,
        status=Attempt.Status.IN_PROGRESS,
    )
    return {
        "attempt_key": str(attempt.attempt_key),
        "quiz_id": quiz.id,
        "user_id": user.id,
        "status": Attempt.Status.IN_PROGRESS,
        "started_at": attempt.started_at.isoformat(),
        "questions": _public_questions(quiz),
    }


def submit_answers(
    attempt_key: UUID | str,
    answers: list[dict[str, Any]],
) -> dict[str, Any]:
    """Grade + complete attempt and enqueue outbox in one transaction (save-only ack)."""
    with transaction.atomic():
        try:
            attempt = (
                Attempt.objects.select_for_update()
                .select_related("user", "quiz")
                .get(attempt_key=attempt_key)
            )
        except Attempt.DoesNotExist as exc:
            raise AttemptNotFound(
                details={"attempt_key": str(attempt_key)}
            ) from exc

        if attempt.status == Attempt.Status.COMPLETED:
            raise AlreadyCompletedError(
                details={"attempt_key": str(attempt.attempt_key)}
            )

        questions = list(
            Question.objects.filter(quiz_id=attempt.quiz_id)
            .prefetch_related("options")
            .order_by("position", "id")
        )
        graded = _validate_and_grade(questions, answers)

        correct_count = sum(1 for row in graded if row["is_correct"])
        total_count = len(questions)
        percent = score_percent(correct_count, total_count)
        message = performance_message_for(percent)
        completed_at = timezone.now()

        AttemptAnswer.objects.bulk_create(
            [
                AttemptAnswer(
                    attempt=attempt,
                    question_id=row["question_id"],
                    option_id=row["option_id"],
                    is_correct=row["is_correct"],
                )
                for row in graded
            ]
        )

        attempt.status = Attempt.Status.COMPLETED
        attempt.completed_at = completed_at
        attempt.correct_count = correct_count
        attempt.total_count = total_count
        attempt.score_percent = percent
        attempt.performance_message = message
        attempt.save(
            update_fields=[
                "status",
                "completed_at",
                "correct_count",
                "total_count",
                "score_percent",
                "performance_message",
            ]
        )

        enqueue_attempt_completed(
            attempt_id=attempt.id,
            payload={
                "user_name": attempt.user.name,
                "user_email": attempt.user.email,
                "quiz_title": attempt.quiz.title,
                "correct_count": correct_count,
                "total_count": total_count,
                "score_percent": percent,
                "performance_message": message,
                "completed_at": completed_at.isoformat(),
                "attempt_id": attempt.id,
            },
        )

        return {
            "saved": True,
            "attempt_key": str(attempt.attempt_key),
            "status": Attempt.Status.COMPLETED,
        }


def get_attempt(attempt_key: UUID | str) -> dict[str, Any]:
    """Return in-progress public shape or completed results + notification_status."""
    try:
        attempt = (
            Attempt.objects.select_related("user", "quiz")
            .prefetch_related(
                Prefetch(
                    "answers",
                    queryset=AttemptAnswer.objects.select_related(
                        "question", "option"
                    ),
                ),
                Prefetch(
                    "quiz__questions",
                    queryset=Question.objects.order_by("position", "id").prefetch_related(
                        Prefetch(
                            "options",
                            queryset=Option.objects.order_by("position", "id"),
                        )
                    ),
                ),
            )
            .get(attempt_key=attempt_key)
        )
    except Attempt.DoesNotExist as exc:
        raise AttemptNotFound(details={"attempt_key": str(attempt_key)}) from exc

    base = {
        "attempt_key": str(attempt.attempt_key),
        "quiz_id": attempt.quiz_id,
        "user_id": attempt.user_id,
        "status": attempt.status,
        "started_at": attempt.started_at.isoformat(),
        "completed_at": (
            attempt.completed_at.isoformat() if attempt.completed_at else None
        ),
    }

    if attempt.status == Attempt.Status.IN_PROGRESS:
        return {
            **base,
            "questions": _public_questions(attempt.quiz),
        }

    answers_by_question = {a.question_id: a for a in attempt.answers.all()}
    breakdown = []
    for question in attempt.quiz.questions.all():
        answer = answers_by_question.get(question.id)
        correct_option = next(o for o in question.options.all() if o.is_correct)
        breakdown.append(
            {
                "question_id": question.id,
                "selected_option_id": answer.option_id if answer else None,
                "correct_option_id": correct_option.id,
                "is_correct": bool(answer and answer.is_correct),
                "explanation": question.explanation,
            }
        )

    from outbox.models import OutboxEvent

    notification_status = None
    outbox = (
        OutboxEvent.objects.filter(uniqueness_key=f"attempt_completed:{attempt.id}")
        .only("status")
        .first()
    )
    if outbox is not None:
        notification_status = outbox.status

    return {
        **base,
        "correct_count": attempt.correct_count,
        "total_count": attempt.total_count,
        "score_percent": attempt.score_percent,
        "performance_message": attempt.performance_message,
        "notification_status": notification_status,
        "breakdown": breakdown,
    }


def list_user_attempts(user_id: int) -> list[dict[str, Any]]:
    """List all attempts for a user, newest first by ``started_at``."""
    if not User.objects.filter(pk=user_id).exists():
        raise UserNotFound(details={"id": user_id})

    attempts = Attempt.objects.filter(user_id=user_id).order_by("-started_at", "-id")
    return [
        {
            "attempt_key": str(a.attempt_key),
            "quiz_id": a.quiz_id,
            "status": a.status,
            "started_at": a.started_at.isoformat(),
            "completed_at": a.completed_at.isoformat() if a.completed_at else None,
            "score_percent": a.score_percent,
        }
        for a in attempts
    ]


def user_stats(user_id: int) -> dict[str, Any]:
    """Aggregate attempt stats for a user (abandoned excluded from averages)."""
    if not User.objects.filter(pk=user_id).exists():
        raise UserNotFound(details={"id": user_id})

    attempts = list(Attempt.objects.filter(user_id=user_id).order_by("quiz_id", "id"))
    total = len(attempts)
    completed = [a for a in attempts if a.status == Attempt.Status.COMPLETED]
    abandoned = [a for a in attempts if a.status == Attempt.Status.IN_PROGRESS]

    by_quiz: dict[int, list[Attempt]] = defaultdict(list)
    for attempt in attempts:
        by_quiz[attempt.quiz_id].append(attempt)

    quizzes = []
    for quiz_id in sorted(by_quiz):
        rows = by_quiz[quiz_id]
        quiz_completed = [
            a for a in rows if a.status == Attempt.Status.COMPLETED
        ]
        quiz_abandoned = [
            a for a in rows if a.status == Attempt.Status.IN_PROGRESS
        ]
        if quiz_completed:
            avg = round(
                sum(a.score_percent for a in quiz_completed) / len(quiz_completed)
            )
        else:
            avg = None
        quizzes.append(
            {
                "quiz_id": quiz_id,
                "completed_attempts": len(quiz_completed),
                "abandoned_attempts": len(quiz_abandoned),
                "average_score_percent": avg,
            }
        )

    return {
        "user_id": user_id,
        "total_attempts": total,
        "completed_attempts": len(completed),
        "abandoned_attempts": len(abandoned),
        "quizzes": quizzes,
    }


def _load_quiz_with_public_questions(quiz_id: int) -> Quiz:
    return (
        Quiz.objects.prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("position", "id").prefetch_related(
                    Prefetch(
                        "options",
                        queryset=Option.objects.order_by("position", "id"),
                    )
                ),
            )
        ).get(pk=quiz_id)
    )


def _public_questions(quiz: Quiz) -> list[dict[str, Any]]:
    return [
        {
            "id": question.id,
            "text": question.text,
            "position": question.position,
            "options": [
                {
                    "id": option.id,
                    "text": option.text,
                    "position": option.position,
                }
                for option in question.options.all()
            ],
        }
        for question in quiz.questions.all()
    ]


def _validate_and_grade(
    questions: list[Question],
    answers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    expected_ids = {q.id for q in questions}
    if not isinstance(answers, list):
        raise IncompleteAnswersError(details={"answers": ["Must be a list."]})

    seen_questions: set[int] = set()
    option_by_id: dict[int, Option] = {}
    for question in questions:
        for option in question.options.all():
            option_by_id[option.id] = option

    graded: list[dict[str, Any]] = []
    for index, row in enumerate(answers):
        if not isinstance(row, dict):
            raise InvalidAnswerError(
                details={"index": index, "reason": "answer must be an object"}
            )
        try:
            question_id = int(row["question_id"])
            option_id = int(row["option_id"])
        except (KeyError, TypeError, ValueError) as exc:
            raise InvalidAnswerError(
                details={"index": index, "reason": "question_id and option_id required"}
            ) from exc

        if question_id not in expected_ids:
            raise InvalidAnswerError(
                details={
                    "question_id": question_id,
                    "reason": "question not on quiz",
                }
            )
        if question_id in seen_questions:
            raise InvalidAnswerError(
                details={
                    "question_id": question_id,
                    "reason": "duplicate question",
                }
            )
        seen_questions.add(question_id)

        option = option_by_id.get(option_id)
        if option is None or option.question_id != question_id:
            raise InvalidAnswerError(
                details={
                    "question_id": question_id,
                    "option_id": option_id,
                    "reason": "option does not belong to question",
                }
            )

        graded.append(
            {
                "question_id": question_id,
                "option_id": option_id,
                "is_correct": option.is_correct,
            }
        )

    missing = expected_ids - seen_questions
    if missing:
        raise IncompleteAnswersError(
            details={"missing_question_ids": sorted(missing)}
        )

    return graded
