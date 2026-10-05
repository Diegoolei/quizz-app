# 08 — TDD test catalog

**Audience:** agents writing red tests, then green implementation.  
**Role:** normative checklist of cases. Pytest modules under `api/tests/` implement these cases (red until domain/HTTP green).  
**Contracts:** each HTTP case must inline the relevant slice from `http/*.md` in the test docstring.

---

## Shared conventions

| Rule | Detail |
|---|---|
| Stack | `pytest` + `pytest-django` + DRF `APIClient` |
| Domain apps | `users`, `quizzes`, `attempts`, `outbox` (models/services/helpers); HTTP under `api` |
| Error asserts | Envelope from [06-api-conventions.md](06-api-conventions.md): `error.code`, `error.message`, `details` |
| Rate limit in domain tests | Raise or disable limit via settings so business tests do not trip 429 |
| Rate limit tests | Use a low override to force 429 quickly |
| Docstrings | Inline request/response/error contract slice |

---

## Helpers and layout

```
api/tests/
  conftest.py                 # APIClient, settings overrides, DB markers
  helpers/
    __init__.py
    factories.py              # user, quiz(N questions × M options), attempt, answers, outbox
    query_growth.py           # assert_selects_do_not_grow(...)
  http/
    test_users.py
    test_quizzes.py
    test_attempts.py
    test_user_progress.py
  test_scoring.py
  test_performance_message.py
  test_attempt_submit.py
  test_outbox.py
  test_outbox_worker.py
  test_data_model.py
  test_seed_data.py
  test_api_conventions.py
  test_rate_limit.py
  test_openapi.py
  test_query_growth.py        # all escalating N+1 cases (grouped)
  test_answer_key_isolation.py
  test_overview_smoke.py
```

### `helpers/query_growth.py` (normative API)

```text
assert_selects_do_not_grow(*, call_endpoint, build_size_s, build_size_2s, k=2) -> None
```

1. `build_size_s()` → call endpoint → count **SELECT** queries → `Q(S)`.
2. Reset / rebuild with `build_size_2s()` → call → `Q(2S)`.
3. Assert `Q(2S) <= Q(S) + k` with **k = 2**.
4. INSERT/UPDATE/BEGIN/COMMIT may grow on writes; **only SELECT growth** fails the assertion.

### `helpers/factories.py`

- `make_user(**kwargs)`
- `make_quiz(*, question_count, options_per_question=2, **kwargs)` — exactly one correct option per question
- `make_attempt(user, quiz, *, status="in_progress")`
- `complete_attempt(attempt, *, answers=None)` — for domain setup when HTTP submit not under test
- `make_outbox_for_attempt(attempt, *, status="pending")`

---

## N+1 / query-growth protocol

Required for **every** `/api/` endpoint. Not a single fixed `assertNumQueries(N)` alone.

| Endpoint | Case id | Scale S → 2S | File |
|---|---|---|---|
| `GET /api/quizzes/` | `QG-QUIZ-LIST` | quiz count 3 → 6 (≥2 questions each) | `test_query_growth.py` |
| `GET /api/quizzes/{id}/` | `QG-QUIZ-DETAIL` | questions 5 → 10 (2 options each) | `test_query_growth.py` |
| `POST /api/quizzes/` | `QG-QUIZ-CREATE` | nested questions in body 5 → 10; SELECT only | `test_query_growth.py` |
| `POST /api/users/` | `QG-USER-CREATE` | pre-existing users 0 → many; create SELECT flat | `test_query_growth.py` |
| `GET /api/users/{id}/` | `QG-USER-GET` | unrelated quizzes/attempts grow; get-by-pk flat | `test_query_growth.py` |
| `POST /api/quizzes/{id}/attempts/` | `QG-ATTEMPT-START` | questions on quiz 5 → 10 | `test_query_growth.py` |
| `POST /api/attempts/{key}/answers/` | `QG-ATTEMPT-SUBMIT` | questions/answers 5 → 10; SELECT flat | `test_query_growth.py` |
| `GET /api/attempts/{key}/` in_progress | `QG-ATTEMPT-GET-IP` | questions 5 → 10 | `test_query_growth.py` |
| `GET /api/attempts/{key}/` completed | `QG-ATTEMPT-GET-DONE` | questions 5 → 10 | `test_query_growth.py` |
| `GET /api/users/{id}/attempts/` | `QG-PROGRESS-LIST` | attempt count 5 → 10 | `test_query_growth.py` |
| `GET /api/users/{id}/stats/` | `QG-PROGRESS-STATS` | 2 quizzes × 3 completed → 2 × 6 completed | `test_query_growth.py` |

---

## A. HTTP — Users

**File:** `api/tests/http/test_users.py`  
**Contract:** [http/users.md](http/users.md)

| Case id | Case | Expect |
|---|---|---|
| `U-POST-201` | Create valid user | 201; body `id`, `name`, `email` |
| `U-POST-422-blank` | Blank name / missing fields | 422 `validation_error` |
| `U-POST-422-email` | Invalid email | 422 `validation_error` |
| `U-POST-409` | Duplicate email | 409 `email_taken` |
| `U-POST-400` | Malformed JSON | 400 `invalid_json` |
| `U-POST-429` | Over rate limit | 429 `rate_limit_exceeded` + `Retry-After` |
| `U-GET-200` | Fetch existing | 200 |
| `U-GET-404` | Unknown id | 404 `user_not_found` |
| `U-GET-429` | Over rate limit | 429 |
| `QG-USER-CREATE` | Query growth | see protocol |
| `QG-USER-GET` | Query growth | see protocol |

---

## B. HTTP — Quizzes

**File:** `api/tests/http/test_quizzes.py`  
**Contract:** [http/quizzes.md](http/quizzes.md)

| Case id | Case | Expect |
|---|---|---|
| `Q-LIST-200` | List quizzes | 200; summaries; no `is_correct` / `explanation` |
| `Q-LIST-429` | Over rate limit | 429 |
| `Q-GET-200` | Retrieve public shape | 200; options without `is_correct`; no `explanation` |
| `Q-GET-404` | Unknown quiz | 404 `quiz_not_found` |
| `Q-GET-429` | Over rate limit | 429 |
| `Q-POST-201` | Create with key | 201; response may include `is_correct` + `explanation` |
| `Q-POST-422-empty` | No questions | 422 `validation_error` |
| `Q-POST-422-options` | <2 options | 422 |
| `Q-POST-422-correct` | ≠1 correct option | 422 |
| `Q-POST-422-explanation` | Blank explanation | 422 |
| `Q-POST-400` | Malformed JSON | 400 |
| `Q-POST-429` | Over rate limit | 429 |
| `QG-QUIZ-LIST` | Query growth | see protocol |
| `QG-QUIZ-DETAIL` | Query growth | see protocol |
| `QG-QUIZ-CREATE` | Query growth | see protocol |

---

## C. HTTP — Attempts

**File:** `api/tests/http/test_attempts.py`  
**Contract:** [http/attempts.md](http/attempts.md)

| Case id | Case | Expect |
|---|---|---|
| `A-START-201` | Start attempt | 201; `attempt_key`; questions without answer key |
| `A-START-404-quiz` | Unknown quiz | 404 `quiz_not_found` |
| `A-START-404-user` | Unknown user | 404 `user_not_found` |
| `A-START-422` | Missing `user_id` | 422 `validation_error` |
| `A-START-429` | Over rate limit | 429 |
| `A-SUB-200` | Submit all answers | 200; `saved: true`; **no** score/breakdown/explanations |
| `A-SUB-outbox` | After submit | Outbox row `pending`, `uniqueness_key=attempt_completed:{id}` |
| `A-SUB-422-incomplete` | Missing question | 422 `incomplete_answers`; attempt stays `in_progress` |
| `A-SUB-422-invalid` | Bad option/question pairing / dupes | 422 `invalid_answer` |
| `A-SUB-409` | Second submit | 409 `attempt_already_completed` |
| `A-SUB-404` | Unknown attempt_key | 404 `attempt_not_found` |
| `A-SUB-429` | Over rate limit | 429 |
| `A-GET-IP` | In-progress GET | No score values; no `is_correct` / `explanation` |
| `A-GET-DONE` | Completed GET | `correct_count`, `score_percent`, `performance_message`, `breakdown`, `notification_status` |
| `A-GET-404` | Unknown key | 404 |
| `A-GET-429` | Over rate limit | 429 |
| `QG-ATTEMPT-START` | Query growth | see protocol |
| `QG-ATTEMPT-SUBMIT` | Query growth | see protocol |
| `QG-ATTEMPT-GET-IP` | Query growth | see protocol |
| `QG-ATTEMPT-GET-DONE` | Query growth | see protocol |

---

## D. HTTP — User progress

**File:** `api/tests/http/test_user_progress.py`  
**Contract:** [http/user-progress.md](http/user-progress.md)

| Case id | Case | Expect |
|---|---|---|
| `P-LIST-200` | List attempts | Newest first; retakes as separate rows; `score_percent` null if in_progress |
| `P-LIST-404` | Unknown user | 404 `user_not_found` |
| `P-LIST-429` | Over rate limit | 429 |
| `P-STATS-200` | Aggregates | Totals; per-quiz `average_score_percent` over **completed only** |
| `P-STATS-ignore-abandoned` | Mix completed + abandoned | Abandoned excluded from average |
| `P-STATS-null-avg` | Only abandoned for a quiz | `average_score_percent` null |
| `P-STATS-404` | Unknown user | 404 |
| `P-STATS-429` | Over rate limit | 429 |
| `QG-PROGRESS-LIST` | Query growth | see protocol |
| `QG-PROGRESS-STATS` | Query growth | see protocol |

---

## E. Domain unit (no HTTP)

| Case id | File | Case |
|---|---|---|
| `D-SCORE-*` | `test_scoring.py` | `correct/total`; `score_percent` via Python 3 `round` |
| `D-MSG-bounds` | `test_performance_message.py` | Bands at 0, 39, 40, 69, 70, 89, 90, 100 |
| `D-SUB-save-only` | `test_attempt_submit.py` | Service/submit path returns ack fields only |
| `D-SUB-incomplete` | `test_attempt_submit.py` | Incomplete rejected; no partial answers |
| `D-SUB-double` | `test_attempt_submit.py` | Second submit conflicts |
| `D-SUB-txn-outbox` | `test_attempt_submit.py` | Answers + complete + outbox one transaction |
| `D-OUT-unique` | `test_outbox.py` | `uniqueness_key` unique |
| `D-OUT-send-fail` | `test_outbox.py` | Send failure does not un-complete attempt |
| `D-WRK-transitions` | `test_outbox_worker.py` | pending→sent / failed→retry / exceeded_retries at 5 |
| `D-WRK-mock-cadence` | `test_outbox_worker.py` | Odd sends fail, even succeed (1-based) |
| `D-MODEL-correct` | `test_data_model.py` | Exactly one `is_correct` per question |
| `D-MODEL-keys` | `test_data_model.py` | `attempt_key` unique; outbox `uniqueness_key` unique |
| `D-SEED` | `test_seed_data.py` | ≥2 quizzes, ≥5 questions each; idempotent re-run |
| `D-ENV` | `test_api_conventions.py` | Envelope on sample 404/422 |
| `D-OAS` | `test_openapi.py` | Schema loads; all `/api/` paths; every path documents 429 |

---

## F. Cross-cutting

| Case id | File | Case |
|---|---|---|
| `X-RL-READ` | `test_rate_limit.py` | GET exceeds → 429 + headers |
| `X-RL-WRITE` | `test_rate_limit.py` | POST exceeds → 429 + headers |
| `X-RL-WORKER` | `test_rate_limit.py` | Outbox management command not rate limited |
| `X-KEY-ISOLATION` | `test_answer_key_isolation.py` | Parametrize list, retrieve, start, in-progress GET — no `is_correct` / `explanation` |
| `X-SMOKE` | `test_overview_smoke.py` | Full happy path (last; after units) |

---

## Suggested red → green order

1. Helpers (`conftest`, factories, `query_growth`) — stubs OK until green  
2. `test_data_model` / conventions  
3. Users + quizzes HTTP  
4. Scoring + performance message + attempt submit + outbox  
5. Attempts HTTP + progress HTTP  
6. Rate limit + OpenAPI  
7. `test_query_growth` (all `QG-*`)  
8. Answer-key isolation + overview smoke  

---

## Out of scope of this catalog file

- Implementing pytest modules or application code (later TDD pass).
