"""Outbox enqueue + worker — `.cursor/specs/05-notifications-outbox.md`."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

import structlog
from django.db import transaction
from django.db.models import Q

from outbox.models import OutboxEvent

EVENT_TYPE_ATTEMPT_COMPLETED = "quiz_attempt_completed"
MAX_RETRIES = 5
DEFAULT_BATCH_SIZE = 50

SendEmail = Callable[[dict[str, Any]], Any]

logger = structlog.get_logger(__name__)


def _email_log_fields(event: OutboxEvent) -> dict[str, Any]:
    payload = event.payload or {}
    fields: dict[str, Any] = {
        "uniqueness_key": event.uniqueness_key,
        "user_email": payload.get("user_email"),
        "quiz_title": payload.get("quiz_title"),
    }
    attempt_id = payload.get("attempt_id")
    if attempt_id is not None:
        fields["attempt_id"] = attempt_id
    score = payload.get("score_percent")
    if score is not None:
        fields["score"] = score
    return fields


def uniqueness_key_for_attempt(attempt_id: int) -> str:
    return f"attempt_completed:{attempt_id}"


def enqueue_attempt_completed(*, attempt_id: int, payload: dict[str, Any]) -> OutboxEvent:
    """Insert a pending outbox row for a completed attempt (same txn as submit)."""
    return OutboxEvent.objects.create(
        event_type=EVENT_TYPE_ATTEMPT_COMPLETED,
        uniqueness_key=uniqueness_key_for_attempt(attempt_id),
        status=OutboxEvent.Status.PENDING,
        retries=0,
        payload=payload,
    )


class MockEmailSender:
    """Deterministic mock: 1-based odd send attempts fail, even succeed."""

    def __init__(self) -> None:
        self._attempts = 0

    def __call__(self, payload: dict[str, Any]) -> None:
        self._attempts += 1
        if self._attempts % 2 == 1:
            raise RuntimeError(f"mock email failure on send attempt {self._attempts}")


# Process-global default for management command / long-running worker ticks.
_default_sender = MockEmailSender()


def process_outbox(
    *,
    send_email: SendEmail | None = None,
    limit: int = DEFAULT_BATCH_SIZE,
) -> int:
    """Process a bounded batch of eligible outbox events.

    Eligible: ``pending``, or ``failed`` with ``retries < MAX_RETRIES``.
    Uses ``SELECT FOR UPDATE SKIP LOCKED`` so overlapping ticks are safe.
    Returns the number of events claimed/processed in this tick.
    """
    if send_email is None:
        send_email = _default_sender

    processed = 0
    with transaction.atomic():
        events = list(
            OutboxEvent.objects.select_for_update(skip_locked=True)
            .filter(
                Q(status=OutboxEvent.Status.PENDING)
                | Q(status=OutboxEvent.Status.FAILED, retries__lt=MAX_RETRIES)
            )
            .order_by("created_at", "id")[:limit]
        )
        for event in events:
            _process_one(event, send_email=send_email)
            processed += 1
    return processed


def _process_one(event: OutboxEvent, *, send_email: SendEmail) -> None:
    try:
        send_email(event.payload)
    except Exception as exc:
        event.retries += 1
        event.last_error = str(exc)
        if event.retries >= MAX_RETRIES:
            event.status = OutboxEvent.Status.EXCEEDED_RETRIES
        else:
            event.status = OutboxEvent.Status.FAILED
        event.save(
            update_fields=["retries", "last_error", "status", "updated_at"]
        )
        log_fn = (
            logger.error
            if event.status == OutboxEvent.Status.EXCEEDED_RETRIES
            else logger.warning
        )
        log_fn(
            "email_send_failed",
            **_email_log_fields(event),
            retries=event.retries,
            status=event.status,
            last_error=event.last_error,
        )
        return

    event.status = OutboxEvent.Status.SENT
    event.last_error = ""
    event.save(update_fields=["status", "last_error", "updated_at"])
    logger.info("email_sent", **_email_log_fields(event))
