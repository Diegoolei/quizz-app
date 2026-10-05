# 03 — Attempts and scoring

## Summary

Start attempt → submit all answers (save-only) → GET results. Single-correct MCQ scoring and performance message bands.

## Start attempt

- Input: `user_id`, quiz id (path).
- Creates Attempt `status=in_progress` with unique `attempt_key`.
- Response includes `attempt_key` and the quiz questions/options **without** answer key.
- Multiple in-progress attempts for the same user+quiz are allowed (abandoned leftovers OK).
- Retake = another start; never overwrites prior attempts.

## Submit answers (save-only)

- Path keyed by `attempt_key`.
- Body: list of `{ question_id, option_id }` covering **every** question in the quiz exactly once.
- Validation failures leave the attempt `in_progress` (no partial Answer rows).
- On success, in **one transaction**:
  1. Persist all `AttemptAnswer` rows with `is_correct`.
  2. Set Attempt `completed`, counts, `score_percent`, `performance_message`, `completed_at`.
  3. Insert `OutboxEvent` with `uniqueness_key=attempt_completed:{attempt_id}`, `status=pending`.
- HTTP response: save ack (`saved`, `attempt_key`, `status`) — **no** score, explanations, or breakdown (see [http/attempts.md](http/attempts.md)).
- Second submit on a completed attempt → conflict error (409).

### Reject when

| Case | Outcome |
|---|---|
| Unknown `attempt_key` | 404 |
| Missing/extra/duplicate question ids | 422 |
| Option not belonging to question / question not on quiz | 422 |
| Incomplete set (not all questions) | 422 |
| Already completed | 409 |

## GET attempt

### In progress

- Return attempt metadata + questions/options without answer key.
- No score fields populated (null or omitted per HTTP contract).
- No explanations / `is_correct` on options.

### Completed

- Return score: `correct_count`, `total_count`, `score_percent`, `performance_message`, `completed_at`.
- Per-question breakdown: selected option, whether correct, explanation, correct option id.
- `notification_status` derived from related outbox event (`pending` / `sent` / `failed` / `exceeded_retries`).

## Scoring

- `correct_count` = number of answers where selected option `is_correct`.
- `total_count` = number of questions on the quiz at submit time.
- `score_percent` = `round(100 * correct_count / total_count)` using half-up / Python `round` half-to-even — **normative for tests: use Python 3 `round`**.

## Performance message bands

| `score_percent` | Message |
|---|---|
| 0–39 | `Keep practicing` |
| 40–69 | `Nice effort` |
| 70–89 | `Great job` |
| 90–100 | `Excellent` |

## Tests

Catalog: `D-SCORE-*`, `D-MSG-bounds`, `D-SUB-*`, `A-*`, `QG-ATTEMPT-*` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_scoring.py` — correct/total and percent
- `api/tests/test_performance_message.py` — band boundaries (0, 39, 40, 69, 70, 89, 90, 100)
- `api/tests/test_attempt_submit.py` — save-only; incomplete; double submit; transactional outbox
- HTTP: `api/tests/http/test_attempts.py`
- `api/tests/test_query_growth.py` — start/submit/GET growth
