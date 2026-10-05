# HTTP — Quizzes

List, retrieve (public take shape), and create (authoring). No update/delete.

**Rate limit:** all endpoints below — 60 req / 60s per IP → `429` `rate_limit_exceeded` (see [06-api-conventions.md](../06-api-conventions.md)).

## GET /api/quizzes/

List quizzes.

### Response — 200

```json
[
  {
    "id": 1,
    "title": "Intro to LLMs",
    "description": "Basics",
    "question_count": 5
  }
]
```

Must not include options, `is_correct`, or `explanation`.

### Errors

| Status | code | When |
|---|---|---|
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## GET /api/quizzes/{id}/

Retrieve quiz for taking (answer-key isolated).

### Response — 200

```json
{
  "id": 1,
  "title": "Intro to LLMs",
  "description": "Basics",
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

**Forbidden fields:** `is_correct`, `explanation` anywhere in the payload.

### Errors

| Status | code | When |
|---|---|---|
| 404 | `quiz_not_found` | Unknown id |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

---

## POST /api/quizzes/

Create quiz with nested answer key (authoring).

### Request

```json
{
  "title": "Intro to LLMs",
  "description": "Basics",
  "questions": [
    {
      "text": "What is a token?",
      "explanation": "Tokens are pieces of text used by models.",
      "position": 1,
      "options": [
        { "text": "A billing unit of text", "is_correct": true, "position": 1 },
        { "text": "A GPU kernel", "is_correct": false, "position": 2 }
      ]
    }
  ]
}
```

### Response — 201

Full quiz including `explanation` and `is_correct` on options (authoring path).

### Errors

| Status | code | When |
|---|---|---|
| 400 | `invalid_json` | Malformed body |
| 422 | `validation_error` | Missing title; no questions; <2 options; ≠1 correct option; blank explanation |
| 429 | `rate_limit_exceeded` | IP exceeded 60 requests / 60s |

### Auth

None.

## Tests

Catalog rows: `Q-*`, `QG-QUIZ-*` in [08-test-catalog.md](../08-test-catalog.md).

- `api/tests/http/test_quizzes.py` — list/retrieve omit key; create returns key; create validation 422; 429
- `api/tests/test_query_growth.py` — `QG-QUIZ-LIST`, `QG-QUIZ-DETAIL`, `QG-QUIZ-CREATE`
- `api/tests/test_answer_key_isolation.py` — list/retrieve never expose answer key
