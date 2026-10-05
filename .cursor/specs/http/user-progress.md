# HTTP — User progress

Attempt history and aggregate stats for a user. No auth.

**Rate limit:** all endpoints below — 60 req / 60s per IP → `429` `rate_limit_exceeded` (see [06-api-conventions.md](../06-api-conventions.md)).

## GET /api/users/{user_id}/attempts/

List all attempts for the user (newest first by `started_at` desc).

### Response — 200

```json
[
  {
    "attempt_key": "550e8400-e29b-41d4-a716-446655440000",
    "quiz_id": 1,
    "status": "completed",
    "started_at": "2026-10-05T00:00:00Z",
    "completed_at": "2026-10-05T00:05:00Z",
    "score_percent": 80
  },
  {
    "attempt_key": "660e8400-e29b-41d4-a716-446655440111",
    "quiz_id": 1,
    "status": "in_progress",
    "started_at": "2026-10-05T01:00:00Z",
    "completed_at": null,
    "score_percent": null
  }
]
```

Does not embed answer-key fields. Detail/results via `GET /api/attempts/{attempt_key}/`.

### Errors

| Status | code | When |
|---|---|---|
| 404 | `user_not_found` | Unknown user_id |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## GET /api/users/{user_id}/stats/

Aggregate progress for the user.

### Response — 200

```json
{
  "user_id": 1,
  "total_attempts": 3,
  "completed_attempts": 2,
  "abandoned_attempts": 1,
  "quizzes": [
    {
      "quiz_id": 1,
      "completed_attempts": 2,
      "abandoned_attempts": 1,
      "average_score_percent": 70
    }
  ]
}
```

`average_score_percent`: mean of completed `score_percent` for that user+quiz (Python 3 `round`); `null` if `completed_attempts == 0` for that quiz. Abandoned attempts excluded from the average.

### Errors

| Status | code | When |
|---|---|---|
| 404 | `user_not_found` | Unknown user_id |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

## Tests

Catalog rows: `P-*`, `QG-PROGRESS-*` in [08-test-catalog.md](../08-test-catalog.md).

- `api/tests/http/test_user_progress.py` — list retakes; stats ignore abandoned; null average; 404/429
- `api/tests/test_query_growth.py` — `QG-PROGRESS-LIST`, `QG-PROGRESS-STATS`
