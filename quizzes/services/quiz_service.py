"""Quiz create/list/retrieve — `.cursor/specs/02-quiz-management.md`."""

from __future__ import annotations

from typing import Any

from django.db import transaction
from django.db.models import Count, Prefetch

from quizzes.models import Option, Question, Quiz
from quizzes.services.exceptions import QuizNotFound, ValidationError


def list_quizzes() -> list[dict[str, Any]]:
    """Return quiz summaries without answer-key fields."""
    quizzes = Quiz.objects.annotate(question_count=Count("questions")).order_by("id")
    return [
        {
            "id": quiz.id,
            "title": quiz.title,
            "description": quiz.description,
            "question_count": quiz.question_count,
        }
        for quiz in quizzes
    ]


def get_quiz_public(quiz_id: int) -> dict[str, Any]:
    """Return quiz take shape without ``is_correct`` / ``explanation``."""
    quiz = (
        Quiz.objects.filter(pk=quiz_id)
        .prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("position", "id").prefetch_related(
                    Prefetch("options", queryset=Option.objects.order_by("position", "id"))
                ),
            )
        )
        .first()
    )
    if quiz is None:
        raise QuizNotFound(details={"quiz_id": quiz_id})
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "questions": [
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
        ],
    }


def create_quiz(
    *,
    title: str,
    description: str = "",
    questions: list[dict[str, Any]],
) -> dict[str, Any]:
    """Create a quiz with nested answer key; return authoring shape."""
    cleaned_title = _require_non_blank(title, field="title")
    cleaned_description = description if isinstance(description, str) else ""
    if not isinstance(questions, list) or len(questions) < 1:
        raise ValidationError(
            "Quiz must include at least one question.",
            details={"questions": ["At least one question is required."]},
        )

    validated_questions = [_validate_question(q, index=i) for i, q in enumerate(questions)]

    with transaction.atomic():
        quiz = Quiz.objects.create(
            title=cleaned_title,
            description=cleaned_description,
        )
        for q_data in validated_questions:
            question = Question.objects.create(
                quiz=quiz,
                text=q_data["text"],
                explanation=q_data["explanation"],
                position=q_data["position"],
            )
            Option.objects.bulk_create(
                [
                    Option(
                        question=question,
                        text=opt["text"],
                        is_correct=opt["is_correct"],
                        position=opt["position"],
                    )
                    for opt in q_data["options"]
                ]
            )

    quiz = (
        Quiz.objects.filter(pk=quiz.id)
        .prefetch_related(
            Prefetch(
                "questions",
                queryset=Question.objects.order_by("position", "id").prefetch_related(
                    Prefetch("options", queryset=Option.objects.order_by("position", "id"))
                ),
            )
        )
        .get()
    )
    return _serialize_authoring(quiz)


def _serialize_authoring(quiz: Quiz) -> dict[str, Any]:
    return {
        "id": quiz.id,
        "title": quiz.title,
        "description": quiz.description,
        "questions": [
            {
                "id": question.id,
                "text": question.text,
                "explanation": question.explanation,
                "position": question.position,
                "options": [
                    {
                        "id": option.id,
                        "text": option.text,
                        "is_correct": option.is_correct,
                        "position": option.position,
                    }
                    for option in question.options.all()
                ],
            }
            for question in quiz.questions.all()
        ],
    }


def _validate_question(raw: dict[str, Any], *, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ValidationError(
            "Each question must be an object.",
            details={"questions": [f"Question at index {index} is invalid."]},
        )
    text = _require_non_blank(raw.get("text"), field=f"questions[{index}].text")
    explanation = _require_non_blank(
        raw.get("explanation"), field=f"questions[{index}].explanation"
    )
    position = raw.get("position", index + 1)
    if not isinstance(position, int) or position < 1:
        raise ValidationError(
            "Question position must be a positive integer.",
            details={f"questions[{index}].position": ["Invalid position."]},
        )

    options = raw.get("options")
    if not isinstance(options, list) or len(options) < 2:
        raise ValidationError(
            "Each question must have at least two options.",
            details={f"questions[{index}].options": ["At least two options required."]},
        )

    validated_options = []
    correct_count = 0
    for o_index, opt in enumerate(options):
        if not isinstance(opt, dict):
            raise ValidationError(
                "Each option must be an object.",
                details={
                    f"questions[{index}].options": [
                        f"Option at index {o_index} is invalid."
                    ]
                },
            )
        opt_text = _require_non_blank(
            opt.get("text"), field=f"questions[{index}].options[{o_index}].text"
        )
        is_correct = bool(opt.get("is_correct", False))
        if is_correct:
            correct_count += 1
        opt_position = opt.get("position", o_index + 1)
        if not isinstance(opt_position, int) or opt_position < 1:
            raise ValidationError(
                "Option position must be a positive integer.",
                details={
                    f"questions[{index}].options[{o_index}].position": [
                        "Invalid position."
                    ]
                },
            )
        validated_options.append(
            {
                "text": opt_text,
                "is_correct": is_correct,
                "position": opt_position,
            }
        )

    if correct_count != 1:
        raise ValidationError(
            "Each question must have exactly one correct option.",
            details={
                f"questions[{index}].options": [
                    "Exactly one option must have is_correct=true."
                ]
            },
        )

    return {
        "text": text,
        "explanation": explanation,
        "position": position,
        "options": validated_options,
    }


def _require_non_blank(value: Any, *, field: str) -> str:
    if value is None or not isinstance(value, str) or not value.strip():
        raise ValidationError(
            f"{field} is required.",
            details={field: ["This field may not be blank."]},
        )
    return value.strip()
