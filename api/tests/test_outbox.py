"""D-OUT-* — outbox uniqueness and fault tolerance (05-notifications-outbox)."""

import pytest


@pytest.mark.django_db
def test_outbox_uniqueness_key_format_and_unique():
    """uniqueness_key = attempt_completed:{attempt_id} and is unique."""
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
    event = make_outbox_for_attempt(attempt)
    assert event.uniqueness_key == f"attempt_completed:{attempt.id}"
    assert OutboxEvent.objects.filter(uniqueness_key=event.uniqueness_key).count() == 1


@pytest.mark.django_db
def test_send_failure_does_not_uncomplete_attempt():
    """Mock send failure updates outbox only; attempt remains completed (AC)."""
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

    # Force failure: injectable sender that always fails (spec: mock may fail).
    def always_fail(_payload):
        raise RuntimeError("smtp boom")

    process_outbox(send_email=always_fail, limit=10)
    attempt.refresh_from_db()
    assert attempt.status == "completed"
    from outbox.models import OutboxEvent

    event = OutboxEvent.objects.get(uniqueness_key=f"attempt_completed:{attempt.id}")
    assert event.status in {"failed", "exceeded_retries"}
