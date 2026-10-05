# 04 — User progress

## Summary

List a user's attempts, inspect a single attempt (via attempt key / progress endpoints), and aggregate stats. Completed attempts drive averages; abandoned do not.

## List attempts for user

- Return all attempts for `user_id`, newest first (by `started_at` or `completed_at`).
- Include: `attempt_key`, `quiz_id`, `status`, `started_at`, `completed_at`, `score_percent` (null if in progress).
- Retakes appear as separate rows.

## Attempt detail

- Same payload rules as GET attempt in [03-attempts-and-scoring.md](03-attempts-and-scoring.md).
- Progress API may deep-link by `attempt_key` already covered under attempts HTTP; user-scoped list is required.

## Aggregate stats

`GET` stats for a user must include at least:

| Field | Definition |
|---|---|
| `total_attempts` | count of all attempts (in_progress + completed) |
| `completed_attempts` | count with `status=completed` |
| `abandoned_attempts` | count with `status=in_progress` |
| `quizzes` | array of per-quiz aggregates |

### Per-quiz aggregate (normative)

For each quiz the user has at least one attempt:

| Field | Definition |
|---|---|
| `quiz_id` | quiz id |
| `completed_attempts` | completed count for that quiz |
| `average_score_percent` | arithmetic mean of `score_percent` over **completed** attempts only; `null` if none completed |
| `best_score_percent` | optional; not required for MVP |
| `abandoned_attempts` | in_progress count for that quiz |

**Formula:**  
`average_score_percent = round(sum(score_percent) / completed_attempts)` using Python 3 `round`, only over completed attempts for that user+quiz.

## Tests

Catalog: `P-*`, `QG-PROGRESS-*` in [08-test-catalog.md](08-test-catalog.md).

- HTTP: `api/tests/http/test_user_progress.py` — averages ignore abandoned; retakes; null average
- `api/tests/test_query_growth.py` — list/stats growth
