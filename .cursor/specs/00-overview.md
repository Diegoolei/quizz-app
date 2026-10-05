# 00 — Overview

## Summary

Django ASGI API for AI-development quizzes: users take quizzes without auth, submit answers in one shot, load scored results separately, and receive a mocked results email via DB outbox + compose cron.

## Actors

| Actor | Notes |
|---|---|
| Anonymous client | No login; passes `user_id` / creates users via API |
| Outbox worker | Cron process every 5s; not an HTTP client of the public API |

## Bounded context

Single service owns: users, quizzes (questions/options/answer key), attempts/answers, scoring, progress aggregates, outbox events, mock email send.

## End-to-end flow

1. `POST /api/users/` — create user (`name`, `email`).
2. `GET /api/quizzes/` — browse.
3. `POST /api/quizzes/{id}/attempts/` with `user_id` — start attempt; response includes `attempt_key` and questions/options **without** correct answers.
4. `POST /api/attempts/{attempt_key}/answers/` — submit **all** answers; response `{ "saved": true }` only; attempt completed; outbox `pending`.
5. `GET /api/attempts/{attempt_key}/` — score, breakdown, explanations, performance message, notification status.
6. Worker claims outbox → mock email → `sent` / `failed` / eventually `exceeded_retries`.
7. `GET /api/users/{id}/attempts/` and `.../stats/` — history and averages; retake starts a new attempt.

## MVP non-goals

- AuthN/AuthZ, real SMTP, quiz update/delete, incremental answers, multi-select/free-text questions, alternate queue systems.

## Related specs

- Product: [main-definition.md](main-definition.md)
- Model: [01-data-model.md](01-data-model.md)
- HTTP: [http/](http/)

## Tests

Catalog: `X-SMOKE` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_overview_smoke.py` — end-to-end happy path (run last after units)
