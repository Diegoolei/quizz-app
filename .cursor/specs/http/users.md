# HTTP — Users

Create and fetch minimal users. No auth.

**Rate limit:** all endpoints below — 60 req / 60s per IP → `429` `rate_limit_exceeded` (see [06-api-conventions.md](../06-api-conventions.md)).

## POST /api/users/

Create a user.

### Request

```json
{
  "name": "Ada Lovelace",
  "email": "ada@example.com"
}
```

### Response — 201

```json
{
  "id": 1,
  "name": "Ada Lovelace",
  "email": "ada@example.com"
}
```

### Errors

| Status | code | When |
|---|---|---|
| 400 | `invalid_json` | Body not JSON / wrong types |
| 422 | `validation_error` | Missing/blank `name` or invalid `email` |
| 409 | `email_taken` | Email already registered |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## GET /api/users/{id}/

Fetch a user by id.

### Response — 200

Same shape as create response.

### Errors

| Status | code | When |
|---|---|---|
| 404 | `user_not_found` | Unknown id |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

## Tests

Catalog rows: `U-*`, `QG-USER-*` in [08-test-catalog.md](../08-test-catalog.md).

- `api/tests/http/test_users.py` — create/get happy paths + 400/409/422/404/429
- `api/tests/test_query_growth.py` — `QG-USER-CREATE`, `QG-USER-GET`
