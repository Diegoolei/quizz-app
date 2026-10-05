"""D-MODEL-* — entity invariants (01-data-model / catalog 08)."""

import pytest
from django.db import IntegrityError


@pytest.mark.django_db
def test_question_requires_exactly_one_correct_option():
    """Invariant: each question has exactly one Option with is_correct=True."""
    from quizzes.models import Option, Question
    from api.tests.helpers.factories import make_quiz

    quiz = make_quiz(question_count=1, options_per_question=2)
    question = Question.objects.get(quiz=quiz)
    correct = Option.objects.filter(question=question, is_correct=True)
    assert correct.count() == 1

    # Marking a second option correct must be rejected by model/constraint/clean.
    other = Option.objects.get(question=question, is_correct=False)
    other.is_correct = True
    with pytest.raises((IntegrityError, ValueError)):
        other.save()


@pytest.mark.django_db
def test_attempt_key_is_unique():
    """Attempt.attempt_key is unique."""
    from attempts.models import Attempt
    from api.tests.helpers.factories import make_attempt, make_quiz, make_user

    user = make_user()
    quiz = make_quiz(question_count=2)
    key = "11111111-1111-1111-1111-111111111111"
    make_attempt(user, quiz, attempt_key=key)
    with pytest.raises(IntegrityError):
        Attempt.objects.create(
            user=user,
            quiz=quiz,
            attempt_key=key,
            status="in_progress",
        )


@pytest.mark.django_db
def test_outbox_uniqueness_key_is_unique():
    """OutboxEvent.uniqueness_key is unique (attempt_completed:{attempt_id})."""
    from outbox.models import OutboxEvent
    from api.tests.helpers.factories import (
        make_attempt,
        make_outbox_for_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=2)
    attempt = make_attempt(user, quiz)
    make_outbox_for_attempt(attempt)
    with pytest.raises(IntegrityError):
        OutboxEvent.objects.create(
            event_type="quiz_attempt_completed",
            status="pending",
            retries=0,
            uniqueness_key=f"attempt_completed:{attempt.id}",
            payload={},
        )
