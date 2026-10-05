# 02 — Quiz management

## Summary

Create quizzes with full answer key; list and retrieve for taking **without** exposing correct answers or explanations. No update or delete in MVP.

## Capabilities

### List quizzes

- Return quiz summaries: `id`, `title`, `description`, question count (optional but recommended).
- Must not embed options' `is_correct` or question `explanation`.

### Retrieve quiz (public take shape)

- Return quiz with questions and options (`id`, `text`, `position` only for options).
- **Must omit** `is_correct` and `explanation`.

### Create quiz (authoring)

- Accept title, description, nested questions with options, exactly one correct option per question, and per-question `explanation`.
- Response **may** include answer-key fields (authoring path). This is the only HTTP path besides completed-attempt results that may expose the key.
- Reject quizzes with < 1 question, questions with < 2 options, or ≠ 1 correct option.

## Out of scope

- `PATCH` / `PUT` / `DELETE` quizzes or nested resources.

## Answer-key isolation

| Surface | `is_correct` | `explanation` |
|---|---|---|
| List | forbidden | forbidden |
| Retrieve (GET quiz) | forbidden | forbidden |
| Create response | allowed | allowed |
| Start attempt payload | forbidden | forbidden |
| In-progress GET attempt | forbidden | forbidden |
| Completed GET attempt | allowed (via results) | allowed |

## Tests

Catalog: `Q-*`, `QG-QUIZ-*`, `X-KEY-ISOLATION` in [08-test-catalog.md](08-test-catalog.md).

- HTTP: `api/tests/http/test_quizzes.py` (see [http/quizzes.md](http/quizzes.md))
- `api/tests/test_answer_key_isolation.py` — list/retrieve safe shape
- `api/tests/test_query_growth.py` — quiz list/detail/create growth
