# 01 — Data model

## Summary

Canonical entities and invariants for MVP persistence. Field types may map to Django equivalents; names below are normative for specs and serializers.

## App ownership

Unrelated bounded contexts live in **separate Django apps**. Closely related tables stay in the same app. Each app owns its `models`, `services/`, and `helpers/` (HTTP may aggregate under `api`).

| App | Models | Owns |
|---|---|---|
| `users` | `User` | user CRUD services/helpers |
| `quizzes` | `Quiz`, `Question`, `Option` | quiz authoring, public quiz reads, seed |
| `attempts` | `Attempt`, `AttemptAnswer` | start/submit/results, scoring, progress aggregates |
| `outbox` | `OutboxEvent` | transactional outbox write helpers, worker/process |

`api` remains the HTTP surface (urls/views/serializers) and shared test package; it must not redefine domain models.

## Entities

### User

| Field | Rules |
|---|---|
| `id` | UUID or big integer PK |
| `name` | non-empty string |
| `email` | valid email; **unique** |

No password, roles, or auth fields.

### Quiz

| Field | Rules |
|---|---|
| `id` | PK |
| `title` | non-empty |
| `description` | optional text |
| `created_at` | set on create |

### Question

| Field | Rules |
|---|---|
| `id` | PK |
| `quiz_id` | FK → Quiz |
| `text` | non-empty |
| `explanation` | non-empty; **answer-key material** — never on public take/browse |
| `position` | ordering within quiz (stable, unique per quiz) |

### Option

| Field | Rules |
|---|---|
| `id` | PK |
| `question_id` | FK → Question |
| `text` | non-empty |
| `is_correct` | boolean; **answer-key material** |
| `position` | ordering within question |

**Invariant:** each question has **≥ 2** options and **exactly one** with `is_correct=true` (single-correct MCQ).

### Attempt

| Field | Rules |
|---|---|
| `id` | PK (internal) |
| `attempt_key` | opaque UUID string; **unique**; public identifier |
| `user_id` | FK → User |
| `quiz_id` | FK → Quiz |
| `status` | `in_progress` \| `completed` |
| `started_at` | set on create |
| `completed_at` | null until successful submit |
| `correct_count` | null until completed |
| `total_count` | null until completed (equals quiz question count at submit) |
| `score_percent` | null until completed; integer 0–100 = `round(100 * correct_count / total_count)` |
| `performance_message` | null until completed; band string from scoring rules |

**Abandoned:** `status=in_progress` with no successful submit. Retakes create a new Attempt row.

### AttemptAnswer

| Field | Rules |
|---|---|
| `id` | PK |
| `attempt_id` | FK → Attempt |
| `question_id` | FK → Question |
| `option_id` | FK → Option (selected) |
| `is_correct` | denormalized at submit time |

**Invariant:** unique `(attempt_id, question_id)`. Written only on successful submit (all-or-nothing).

### OutboxEvent

| Field | Rules |
|---|---|
| `id` | PK |
| `event_type` | e.g. `quiz_attempt_completed` |
| `payload` | JSON (email fields + attempt/user/quiz ids) |
| `status` | `pending` \| `sent` \| `failed` \| `exceeded_retries` |
| `retries` | int ≥ 0; default 0 |
| `uniqueness_key` | string; **unique**; value `attempt_completed:{attempt_id}` |
| `created_at` | set on insert |
| `updated_at` | set on status/retry changes |
| `last_error` | optional text |

Max retries before `exceeded_retries`: **5** (see [05-notifications-outbox.md](05-notifications-outbox.md)).

## Cross-entity invariants

- Attempt answers may only reference questions/options belonging to the attempt's quiz.
- Completing an attempt and inserting its outbox event are **one transaction**.
- Answer-key fields (`Option.is_correct`, `Question.explanation`) must not leak via public serializers for list/retrieve/in-progress.

## Tests

Catalog: `D-MODEL-*` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_data_model.py` — single-correct constraint; `attempt_key` uniqueness; outbox `uniqueness_key` uniqueness
