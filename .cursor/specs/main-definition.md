# Main definition — Quiz App API

**Audience:** agents implementing or changing this repo.  
**Role of this file:** product-level contract (what must exist). It is not an HTTP contract and not an implementation plan.  
**Detail lives elsewhere:** see [README.md](README.md) for the full spec tree. When behavior changes, update those specs first (spec → red → green).

---

## Goal

Build a **backend-focused RESTful API** for a quiz app on AI development concepts. Users take quizzes, track progress, get scored feedback, and receive an async (mocked) results email via an **outbox + cron worker**.

Focus: backend logic, persistence, and asynchronous workflows — not a polished UI.

---

## In scope

| Area | Users / system must be able to |
|---|---|
| Users | Create and fetch a user with minimal fields (`id`, `name`, `email`). No authentication or authorization. |
| Quiz management | List quizzes; retrieve a quiz with questions and options; create a quiz (questions, options, correct answers, explanations). No update/delete. |
| Attempts | Start an attempt (receive opaque `attempt_key` + questions/options without answer key); submit **all** answers in one request (**save-only ack**); fetch results on a separate endpoint. |
| Results payload | Overall score; per-question correctness + explanations; short score-based performance message; notification status. |
| Progress | List a user's attempts; fetch one attempt's detailed results; aggregate stats (total completed attempts, **average % of completed attempts per user per quiz**). |
| Retakes | Starting again creates a **new** attempt; prior attempts stay. Abandoned attempts (started, never successfully submitted) are allowed. |
| Notifications | Successful submit writes an outbox event in the **same DB transaction** as answers; a compose cron every **5s** processes the outbox with a mocked email sender. |

## Out of scope

- Real email delivery (use a mock with controlled failures)
- Authentication / authorization
- Frontend / SPA
- Quiz update / delete
- Alternate async stacks (Celery, RQ, etc.) — MVP uses **DB outbox + docker-compose cron**

---

## Hard constraints (non-negotiable)

1. **Answer-key isolation**  
   Correct answers and explanations must **not** appear on quiz list/retrieve or on an in-progress attempt. They appear **only** in results of a **completed** attempt (and on quiz **create** authoring responses). Public take paths never expose the key.

2. **Submit is save-only**  
   Submit validates and persists answers, marks the attempt completed, and enqueues the outbox event. Response is an ack (`saved: true`) — **not** the score. Clients load score/breakdown via the results endpoint.

3. **Submit requires a complete answer set**  
   Every question in the quiz must have exactly one selected option in the request. Incomplete sets are rejected; attempt stays in progress (abandoned until a valid submit).

4. **Async notification via outbox**  
   - Outbox row fields: `event_type`, `payload`, `retries`, `created_at`, `uniqueness_key` (unique; one event per completed attempt).  
   - Statuses: `pending` \| `sent` \| `failed` \| `exceeded_retries`.  
   - Outbox insert failure fails the submit transaction.  
   - **Send** failure never rolls back a completed submit; status/retries are updated by the worker.  
   - Mock email fails every other send attempt (deterministic 50% failure for tests).  
   - Worker runs every 5 seconds from docker-compose.

5. **Email content (when sent)** must include:  
   user name, user email, quiz title, score (correct/total), percentage, performance message, completion timestamp.

6. **Persistence** must cover:  
   users; quizzes → questions → options → correct answers + explanations; attempts; per-attempt answers; outbox / notification status.

7. **OpenAPI**  
   Every endpoint and every documented error response must appear in OpenAPI.

8. **Rate limiting**  
   All `/api/` endpoints are rate limited by client IP (**60 requests / 60 seconds**). Exceeded → **429** `rate_limit_exceeded` with `Retry-After`. Details in [06-api-conventions.md](06-api-conventions.md).

---

## Scoring and messages

- Per attempt: `correct / total` (single-correct MCQ); percentage = rounded as defined in module specs.  
- Aggregate per user per quiz: **average percentage of completed attempts only** (abandoned excluded).  
- Performance message bands:  
  - 0–39: `Keep practicing`  
  - 40–69: `Nice effort`  
  - 70–89: `Great job`  
  - 90–100: `Excellent`

---

## Illustrative happy path (orientation only)

1. Create/fetch user → list quizzes → start attempt → receive `attempt_key` and questions/options **without** correct answers.  
2. Submit all answers → receive **save ack only**; attempt is completed; outbox row is `pending`.  
3. GET attempt results → score (e.g. 4/5, 80%), per-question correctness, explanations, performance message, notification status.  
4. Cron processes outbox; mock email may fail and retry until `sent` or `exceeded_retries`.  
5. Later: view history / stats; retake → new attempt; previous attempts preserved.

---

## Acceptance criteria

- [ ] Capabilities in **In scope** are implemented and functional  
- [ ] Correct answers never exposed on public take/browse paths before completion  
- [ ] Submit is save-only; results via separate endpoint  
- [ ] Attempts persist and remain retrievable across retakes; abandoned attempts allowed  
- [ ] Outbox + 5s cron worker with mocked email  
- [ ] Send failures do not fail quiz submission  
- [ ] Notification status tracked (`pending` / `sent` / `failed` / `exceeded_retries`)  
- [ ] Seed data: **≥ 2 quizzes**, each with **≥ 5 questions**  
- [ ] OpenAPI covers all endpoints and errors (including 429)  
- [ ] Rate limiting enforced on all `/api/` endpoints  
- [ ] Unit tests at least cover: scoring; performance-message calculation; outbox/async workflow behavior; rate-limit 429 

---

## Spec map

| Kind | Path |
|---|---|
| This product contract | `.cursor/specs/main-definition.md` |
| Index | `.cursor/specs/README.md` |
| Module requirements | `.cursor/specs/0*.md` |
| Test catalog (TDD cases + N+1) | `.cursor/specs/08-test-catalog.md` |
| HTTP contracts | `.cursor/specs/http/*.md` |

Concrete API shapes and data models live in module + HTTP specs — not here.

---

## Production judgment

Apply production practices of highest leverage for this service (validation, transactions, structured logging, idempotent outbox). Prefer explicit trade-offs over checklist compliance.
