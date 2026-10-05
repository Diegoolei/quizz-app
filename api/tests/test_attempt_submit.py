"""D-SUB-* — submit service: save-only, validation, transactional outbox (03 / 05)."""

import pytest


@pytest.mark.django_db
def test_submit_persists_answers_and_outbox_in_one_transaction():
    """Successful submit grades, completes attempt, inserts outbox pending — one atomic unit."""
    from attempts.models import AttemptAnswer
    from attempts.services.attempt_service import submit_answers
    from outbox.models import OutboxEvent
    from api.tests.helpers.factories import (
        all_correct_answers_payload,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=5)
    attempt = make_attempt(user, quiz)
    result = submit_answers(attempt.attempt_key, all_correct_answers_payload(quiz)["answers"])

    assert result == {
        "saved": True,
        "attempt_key": attempt.attempt_key,
        "status": "completed",
    }
    attempt.refresh_from_db()
    assert attempt.status == "completed"
    assert AttemptAnswer.objects.filter(attempt=attempt).count() == 5
    assert OutboxEvent.objects.filter(
        uniqueness_key=f"attempt_completed:{attempt.id}",
        status="pending",
    ).exists()
    # Save-only: no score keys on service ack
    assert "score_percent" not in result
    assert "breakdown" not in result


@pytest.mark.django_db
def test_submit_incomplete_leaves_attempt_in_progress():
    """Missing question → rejected; no AttemptAnswer rows; status stays in_progress."""
    from attempts.models import AttemptAnswer
    from attempts.services.attempt_service import IncompleteAnswersError, submit_answers
    from api.tests.helpers.factories import make_attempt, make_quiz, make_user

    user = make_user()
    quiz = make_quiz(question_count=3)
    attempt = make_attempt(user, quiz)
    with pytest.raises(IncompleteAnswersError):
        submit_answers(attempt.attempt_key, [])
    attempt.refresh_from_db()
    assert attempt.status == "in_progress"
    assert AttemptAnswer.objects.filter(attempt=attempt).count() == 0


@pytest.mark.django_db
def test_submit_twice_conflicts():
    """Second submit on completed attempt raises conflict."""
    from attempts.services.attempt_service import AlreadyCompletedError, submit_answers
    from api.tests.helpers.factories import (
        all_correct_answers_payload,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=2)
    attempt = make_attempt(user, quiz)
    answers = all_correct_answers_payload(quiz)["answers"]
    submit_answers(attempt.attempt_key, answers)
    with pytest.raises(AlreadyCompletedError):
        submit_answers(attempt.attempt_key, answers)
