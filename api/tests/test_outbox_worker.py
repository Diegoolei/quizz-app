"""D-WRK-* — worker transitions and mock fail cadence (05 / http/outbox)."""

import pytest


@pytest.mark.django_db
def test_worker_odd_send_fails_even_succeeds():
    """Mock email: 1-based odd attempts fail, even succeed."""
    from outbox.models import OutboxEvent
    from outbox.services.outbox_service import MockEmailSender, process_outbox
    from api.tests.helpers.factories import (
        complete_attempt,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=2)
    a1 = make_attempt(user, quiz)
    complete_attempt(a1)
    a2 = make_attempt(user, quiz)
    complete_attempt(a2)

    sender = MockEmailSender()
    process_outbox(send_email=sender, limit=10)

    e1 = OutboxEvent.objects.get(uniqueness_key=f"attempt_completed:{a1.id}")
    e2 = OutboxEvent.objects.get(uniqueness_key=f"attempt_completed:{a2.id}")
    assert e1.status == "failed"
    assert e1.retries == 1
    assert e2.status == "sent"


@pytest.mark.django_db
def test_worker_exceeded_retries_at_five():
    """After 5 failed sends, status becomes exceeded_retries."""
    from outbox.models import OutboxEvent
    from outbox.services.outbox_service import process_outbox
    from api.tests.helpers.factories import (
        complete_attempt,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user()
    quiz = make_quiz(question_count=2)
    attempt = make_attempt(user, quiz)
    complete_attempt(attempt)

    def always_fail(_payload):
        raise RuntimeError("fail")

    for _ in range(5):
        process_outbox(send_email=always_fail, limit=10)

    event = OutboxEvent.objects.get(uniqueness_key=f"attempt_completed:{attempt.id}")
    assert event.retries == 5
    assert event.status == "exceeded_retries"
