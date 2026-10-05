"""D-WRK-* — worker transitions and mock fail cadence (05 / http/outbox)."""

import pytest
from structlog.testing import capture_logs


@pytest.mark.django_db
def test_worker_logs_email_sent_on_success():
    """On successful mock send, structured log includes attempt/email/quiz/score."""
    from outbox.services.outbox_service import process_outbox
    from api.tests.helpers.factories import (
        complete_attempt,
        make_attempt,
        make_quiz,
        make_user,
    )

    user = make_user(email="ops@example.com")
    quiz = make_quiz(question_count=2, title="Ops Quiz")
    attempt = make_attempt(user, quiz)
    complete_attempt(attempt)

    with capture_logs() as logs:
        process_outbox(send_email=lambda _payload: None, limit=10)

    sent = [e for e in logs if e.get("event") == "email_sent"]
    assert len(sent) == 1
    entry = sent[0]
    assert entry["attempt_id"] == attempt.id
    assert entry["uniqueness_key"] == f"attempt_completed:{attempt.id}"
    assert entry["user_email"] == "ops@example.com"
    assert entry["quiz_title"] == "Ops Quiz"
    assert entry["score"] == attempt.score_percent


@pytest.mark.django_db
def test_worker_logs_failure_and_retry():
    """Failed send logs warning with retries/status; exceeded_retries at error."""
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
        raise RuntimeError("smtp boom")

    with capture_logs() as logs:
        process_outbox(send_email=always_fail, limit=10)

    failed = [e for e in logs if e.get("event") == "email_send_failed"]
    assert len(failed) == 1
    assert failed[0]["log_level"] == "warning"
    assert failed[0]["retries"] == 1
    assert failed[0]["status"] == "failed"
    assert "smtp boom" in failed[0]["last_error"]

    event = OutboxEvent.objects.get(uniqueness_key=f"attempt_completed:{attempt.id}")
    event.retries = 4
    event.status = "failed"
    event.save(update_fields=["retries", "status", "updated_at"])

    with capture_logs() as logs:
        process_outbox(send_email=always_fail, limit=10)

    exceeded = [e for e in logs if e.get("event") == "email_send_failed"]
    assert len(exceeded) == 1
    assert exceeded[0]["log_level"] == "error"
    assert exceeded[0]["status"] == "exceeded_retries"
    assert exceeded[0]["retries"] == 5


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
