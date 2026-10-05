# HTTP — Outbox / notifications

MVP exposes notification status on completed attempt GET only. There is **no** public create/update/list API for outbox rows. This file documents worker behavior and the status surface for OpenAPI/tests.

**Rate limit:** the public read surface is `GET /api/attempts/{attempt_key}/`, which is rate limited (60 req / 60s per IP → `429`). The outbox worker is non-HTTP and is **not** rate limited.

## Public surface

### Read — via attempts

`GET /api/attempts/{attempt_key}/` when `status=completed` includes:

```json
"notification_status": "pending"
```

Values: `pending` | `sent` | `failed` | `exceeded_retries`.

Mapped from the single `OutboxEvent` with `uniqueness_key=attempt_completed:{attempt_id}`.

See [attempts.md](attempts.md) for full response and errors.

### Mutate

None (out of scope).

## Worker (non-HTTP)

| Item | Contract |
|---|---|
| Trigger | docker-compose service / cron every **5 seconds** |
| Command | management command (e.g. `process_outbox`) |
| Eligible rows | `pending`, or `failed` with `retries < 5` |
| Success | `status=sent` |
| Failure | increment `retries`; `failed` or `exceeded_retries` at max 5 |
| Mock email | fail every odd send attempt (1-based); succeed on even |
| Concurrency | safe under overlapping ticks (`SKIP LOCKED` or equivalent) |

Domain rules: [05-notifications-outbox.md](../05-notifications-outbox.md).

## OpenAPI

- Document `notification_status` enum on completed Attempt schema.
- Document `429` on the attempt GET used for notification status (owned by [attempts.md](attempts.md)).
- Do not document public outbox CRUD paths.

## Errors

N/A for worker. Attempt GET errors remain in [attempts.md](attempts.md).

### Auth

None.

## Tests

Catalog rows: `D-OUT-*`, `D-WRK-*`, `A-SUB-outbox`, `A-GET-DONE` in [08-test-catalog.md](../08-test-catalog.md).

- `api/tests/test_outbox.py` — uniqueness_key; same-txn; send failure does not uncomplete
- `api/tests/test_outbox_worker.py` — transitions; mock fail cadence; exceeded_retries
- `api/tests/http/test_attempts.py` — `notification_status` on completed results
- `api/tests/test_rate_limit.py` — worker not rate limited (`X-RL-WORKER`)
