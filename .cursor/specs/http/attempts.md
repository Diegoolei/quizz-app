# HTTP — Attempts

Start attempt, submit answers (save-only), fetch attempt (in-progress or results).

**Rate limit:** all endpoints below — 60 req / 60s per IP → `429` `rate_limit_exceeded` (see [06-api-conventions.md](../06-api-conventions.md)).

## POST /api/quizzes/{quiz_id}/attempts/

Start a new attempt for a user.

### Request

```json
{
  "user_id": 1
}
```

### Response — 201

```json
{
  "attempt_key": "550e8400-e29b-41d4-a716-446655440000",
  "quiz_id": 1,
  "user_id": 1,
  "status": "in_progress",
  "started_at": "2026-10-05T00:00:00Z",
  "questions": [
    {
      "id": 10,
      "text": "What is a token?",
      "position": 1,
      "options": [
        { "id": 100, "text": "A billing unit of text", "position": 1 },
        { "id": 101, "text": "A GPU kernel", "position": 2 }
      ]
    }
  ]
}
```

**Forbidden fields:** `is_correct`, `explanation`.

### Errors

| Status | code | When |
|---|---|---|
| 400 | `invalid_json` | Malformed body |
| 404 | `quiz_not_found` | Unknown quiz |
| 404 | `user_not_found` | Unknown user_id |
| 422 | `validation_error` | Missing user_id |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## POST /api/attempts/{attempt_key}/answers/

Submit **all** answers for an in-progress attempt. **Save-only** — no score in response.

### Request

```json
{
  "answers": [
    { "question_id": 10, "option_id": 100 },
    { "question_id": 11, "option_id": 110 }
  ]
}
```

Must include exactly one entry per question on the quiz.

### Response — 200

```json
{
  "saved": true,
  "attempt_key": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed"
}
```

Must **not** include score, breakdown, explanations, or correct option ids.

Side effects (same transaction): persist answers, complete attempt, insert outbox `pending` with `uniqueness_key=attempt_completed:{attempt_id}`.

### Errors

| Status | code | When |
|---|---|---|
| 400 | `invalid_json` | Malformed body |
| 404 | `attempt_not_found` | Unknown attempt_key |
| 409 | `attempt_already_completed` | Second submit |
| 422 | `incomplete_answers` | Missing question(s) |
| 422 | `invalid_answer` | Unknown question/option, option≠question, duplicates, extras |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## GET /api/attempts/{attempt_key}/

Fetch attempt. Shape depends on status.

### Response — 200 (in_progress)

```json
{
  "attempt_key": "550e8400-e29b-41d4-a716-446655440000",
  "quiz_id": 1,
  "user_id": 1,
  "status": "in_progress",
  "started_at": "2026-10-05T00:00:00Z",
  "completed_at": null,
  "questions": [
    {
      "id": 10,
      "text": "What is a token?",
      "position": 1,
      "options": [
        { "id": 100, "text": "A billing unit of text", "position": 1 },
        { "id": 101, "text": "A GPU kernel", "position": 2 }
      ]
    }
  ]
}
```

**Forbidden:** score fields with values, `is_correct`, `explanation`, `notification_status` (or null).

### Response — 200 (completed)

```json
{
  "attempt_key": "550e8400-e29b-41d4-a716-446655440000",
  "quiz_id": 1,
  "user_id": 1,
  "status": "completed",
  "started_at": "2026-10-05T00:00:00Z",
  "completed_at": "2026-10-05T00:05:00Z",
  "correct_count": 4,
  "total_count": 5,
  "score_percent": 80,
  "performance_message": "Great job",
  "notification_status": "pending",
  "breakdown": [
    {
      "question_id": 10,
      "selected_option_id": 100,
      "correct_option_id": 100,
      "is_correct": true,
      "explanation": "Tokens are pieces of text used by models."
    }
  ]
}
```

`notification_status` ∈ `pending` | `sent` | `failed` | `exceeded_retries`.

### Errors

| Status | code | When |
|---|---|---|
| 404 | `attempt_not_found` | Unknown attempt_key |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

## Tests

Catalog rows: `A-*`, `QG-ATTEMPT-*` in [08-test-catalog.md](../08-test-catalog.md).

- `api/tests/http/test_attempts.py` — start omits key; submit save-only; incomplete 422; double submit 409; completed results + `notification_status`; 429
- `api/tests/test_query_growth.py` — `QG-ATTEMPT-START`, `QG-ATTEMPT-SUBMIT`, `QG-ATTEMPT-GET-IP`, `QG-ATTEMPT-GET-DONE`
- `api/tests/test_answer_key_isolation.py` — start + in-progress GET never expose answer key
