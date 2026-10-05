"""Public outbox service entrypoints."""

from outbox.services.outbox_service import (
    DEFAULT_BATCH_SIZE,
    EVENT_TYPE_ATTEMPT_COMPLETED,
    MAX_RETRIES,
    MockEmailSender,
    enqueue_attempt_completed,
    process_outbox,
    uniqueness_key_for_attempt,
)

__all__ = [
    "DEFAULT_BATCH_SIZE",
    "EVENT_TYPE_ATTEMPT_COMPLETED",
    "MAX_RETRIES",
    "MockEmailSender",
    "enqueue_attempt_completed",
    "process_outbox",
    "uniqueness_key_for_attempt",
]
