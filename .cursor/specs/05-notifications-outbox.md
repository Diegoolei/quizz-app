# 05 — Notifications (outbox)

## Summary

Transactional outbox for results emails. Worker in docker-compose runs every 5 seconds. Mock sender fails every other send for deterministic retries.

## Event write (submit path)

On successful answer submit, same DB transaction as answers + attempt completion:

```
OutboxEvent(
  event_type="quiz_attempt_completed",
  uniqueness_key="attempt_completed:{attempt_id}",
  status="pending",
  retries=0,
  payload={ ... email fields ... }
)
```

- Duplicate `uniqueness_key` must not create a second event (DB unique constraint). Re-submit is blocked at attempt layer (409) before outbox insert.
- If outbox insert fails, entire submit rolls back (attempt stays `in_progress`, no answers).

## Payload (email content)

Must include:

| Key | Source |
|---|---|
| `user_name` | User.name |
| `user_email` | User.email |
| `quiz_title` | Quiz.title |
| `correct_count` | Attempt.correct_count |
| `total_count` | Attempt.total_count |
| `score_percent` | Attempt.score_percent |
| `performance_message` | Attempt.performance_message |
| `completed_at` | Attempt.completed_at (ISO-8601) |
| `attempt_id` | Attempt.id (internal correlation) |

## Statuses

| Status | Meaning |
|---|---|
| `pending` | never successfully processed; eligible for worker |
| `sent` | mock email succeeded; terminal |
| `failed` | last send failed; eligible for retry while `retries < max` |
| `exceeded_retries` | `retries` reached max; terminal |

**Max retries:** 5. When a send fails and `retries + 1 >= 5`, set `exceeded_retries` (and set `retries` to 5). Otherwise set `failed` and increment `retries`.

Clarify processing:

1. Claim rows in `pending` or `failed` with `retries < 5`.
2. Call mock email.
3. On success → `sent`.
4. On failure → increment `retries`; if `retries >= 5` → `exceeded_retries`, else → `failed`; store `last_error`.

## Worker

- Invoked every **5 seconds** via docker-compose (sidecar or cron service running a management command, e.g. `process_outbox`).
- Compose `outbox-worker` must **not** use the web `entrypoint.sh` (no migrate/collectstatic); override `entrypoint` and loop `process_outbox` + sleep 5; depend on healthy `db`.
- Process a bounded batch per tick (implementation choice; document default batch size in code, e.g. 50).
- Must be safe if overlapping ticks occur (row-level lock / `SELECT FOR UPDATE SKIP LOCKED` or equivalent).

## Operator logging

On successful mock send, emit a structured log (event name equivalent to **email sent** / `email_sent`) including when present:

| Field | Source |
|---|---|
| `attempt_id` | payload |
| `uniqueness_key` | OutboxEvent |
| `user_email` | payload |
| `quiz_title` | payload |
| `score` | payload `score_percent` (omit if absent) |

On send failure / retry: log at warning (include `retries`, `last_error`, resulting `status`). On `exceeded_retries`: log at error.

## Mock email failure policy

- Deterministic for tests: maintain a process-global (or DB-backed test double) send counter; **every odd-numbered send attempt fails**, every even succeeds (1-based: fail, succeed, fail, succeed…).
- Equivalent statement: roughly one failure each two tries.
- Unit tests must not depend on wall-clock randomness.

## Fault tolerance

| Failure | Submit HTTP | Attempt state |
|---|---|---|
| Outbox insert error | fails | unchanged (in_progress) |
| Mock send error | N/A (async) | remains completed; outbox `failed` / retry |
| Worker down | N/A | completed; outbox stays `pending` |

Notification status is **queryable** on completed attempt GET (`notification_status`). No public mutate endpoint for outbox in MVP.

## Tests

Catalog: `D-OUT-*`, `D-WRK-*` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_outbox.py` — uniqueness_key; same-txn with submit; send failure does not uncomplete attempt
- `api/tests/test_outbox_worker.py` — status transitions; max retries → `exceeded_retries`; mock fail every other send; structured `email_sent` / failure logs
- HTTP/docs: [http/outbox.md](http/outbox.md)
