# 06 — API conventions

## Summary

Shared HTTP/JSON rules for MVP. No authentication. All endpoints and errors must be in OpenAPI.

## Base

- Prefix: `/api/`
- Content-Type: `application/json`
- Trailing slashes: follow Django/DRF default (trailing slash required).

## Auth

- None. Clients create users and pass `user_id` / `attempt_key` as opaque identifiers.
- Knowing an id/key is sufficient to act (acceptable for this MVP; document risk in README later if needed).

## Rate limiting

All public `/api/` endpoints are rate limited (no auth → key by client IP).

| Rule | Value |
|---|---|
| Scope | Every route under `/api/` documented in `http/*.md` |
| Key | Client IP (`REMOTE_ADDR`; honor `X-Forwarded-For` only when behind a trusted proxy) |
| Limit | **60 requests per 60-second fixed window** per IP |
| Exceeded | HTTP **429** with error envelope `code=rate_limit_exceeded` |
| Headers (required on 429; recommended on 2xx) | `Retry-After` (seconds until window reset); `X-RateLimit-Limit`; `X-RateLimit-Remaining`; `X-RateLimit-Reset` (unix epoch seconds) |

### 429 body

```json
{
  "error": {
    "code": "rate_limit_exceeded",
    "message": "Too many requests. Try again later.",
    "details": {}
  }
}
```

### Implementation notes (normative for tests)

- Applied before view business logic (middleware or DRF throttle).
- Configurable via settings/env for local/tests (e.g. raise limit or disable); **default production/staging values match the table above**.
- OpenAPI must document `429` / `rate_limit_exceeded` on **every** `/api/` operation.
- Outbox worker is not HTTP and is not rate limited.

## Identifiers

| Resource | Public id |
|---|---|
| User | `id` |
| Quiz / Question / Option | numeric/UUID `id` |
| Attempt | `attempt_key` (UUID string), not internal PK |

## Success responses

- `200` GET / successful submit ack
- `201` create user / create quiz / start attempt
- Bodies are JSON objects or lists as per HTTP specs.

## Error envelope

All 4xx/5xx JSON errors use:

```json
{
  "error": {
    "code": "snake_case_machine_code",
    "message": "human-readable summary",
    "details": {}
  }
}
```

- `details` may be a field map for validation errors (DRF-style) or empty object.
- `code` values are listed per endpoint in HTTP specs; must appear in OpenAPI.

## Common status codes

| Status | Use |
|---|---|
| 400 | Malformed JSON / wrong types |
| 404 | Unknown resource id / attempt_key; unmatched `/api/` route (see below) |
| 409 | Conflict (e.g. double submit, duplicate email) |
| 422 | Semantically invalid body (incomplete answers, bad option/question pairing, quiz create invariants) |
| 429 | Rate limit exceeded (all `/api/` endpoints) |
| 500 | Unexpected server error |

## Unmatched `/api/` routes

Requests under `/api/` that do not match any configured route — including **empty path parameters** (e.g. `GET /api/quizzes//` when `{id}` is missing/empty) — MUST return HTTP **404** with the standard error envelope and `code=not_found`.

```json
{
  "error": {
    "code": "not_found",
    "message": "Not found.",
    "details": {}
  }
}
```

- **Must not** return Django's HTML technical/debug 404 page for `/api/` paths, including when `DEBUG=True`.
- Resource-specific 404s that *do* match a route (e.g. unknown quiz id on `GET /api/quizzes/{id}/`) keep their endpoint codes (`quiz_not_found`, etc.).
- Non-`/api/` unmatched routes may keep Django's default HTML 404.

## OpenAPI

- Served via project OpenAPI/Swagger integration (e.g. `drf-spectacular` or equivalent).
- **Must** document every route in `http/*.md` and every error status/code listed there.
- Schemas must not advertise answer-key fields on public take/browse operations.

## Pagination

- MVP: no pagination required; lists return full arrays. If added later, update this spec first.

## Tests

Catalog: `D-ENV`, `D-ENV-EMPTY-PATH`, `D-OAS`, `X-RL-*` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_api_conventions.py` — error envelope shape on a sample 404/422; empty path param (`/api/quizzes//`) → JSON `not_found` (not HTML)
- `api/tests/test_rate_limit.py` — 429 + `rate_limit_exceeded` + `Retry-After` on read and write; worker exempt
- `api/tests/test_openapi.py` — schema loads; key paths present; every path documents 429
