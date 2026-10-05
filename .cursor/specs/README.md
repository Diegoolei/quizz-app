# Specs index

Agent-oriented contracts for the Quiz App API. **Behavior changes require an updated spec in the same change set**, then failing tests, then implementation (spec → red → green).

## Reading order

1. [main-definition.md](main-definition.md) — product contract (what must exist)
2. [00-overview.md](00-overview.md) — context and end-to-end flow
3. [01-data-model.md](01-data-model.md) — entities and invariants
4. [06-api-conventions.md](06-api-conventions.md) — HTTP/JSON/errors/OpenAPI
5. Domain modules: [02](02-quiz-management.md) → [03](03-attempts-and-scoring.md) → [04](04-user-progress.md) → [05](05-notifications-outbox.md) → [07](07-seed-data.md)
6. [08-test-catalog.md](08-test-catalog.md) — TDD case matrix + N+1 query-growth protocol
7. HTTP contracts under [http/](http/)

## Ownership

| Kind | Path | Contains |
|---|---|---|
| Product | `main-definition.md` | Goals, scope, hard constraints, acceptance |
| Module | `0*.md` | Domain rules, invariants, scoring, outbox, seed, test catalog |
| HTTP | `http/*.md` | Method, path, request/response, errors, auth, tests |

## HTTP template (minimum)

1. Title and summary  
2. Request — method, path, body/query  
3. Response — status codes and body shape  
4. Errors — status + when  
5. Auth — none for MVP  
6. Tests — exact pytest path(s)  

## Hard cross-cutting rules

- Public quiz / in-progress attempt responses never include `is_correct` or `explanation`.
- Attempt results expose answer-key fields only for **completed** attempts.
- Submit is save-only; scoring appears on GET results.
- Outbox write shares the submit transaction; send failures never unwind submit.
- All `/api/` endpoints are rate limited (60/min per IP → 429); see [06-api-conventions.md](06-api-conventions.md).
- Every `/api/` endpoint has an escalating N+1 check (`Q(2S) <= Q(S) + 2` on SELECTs); see [08-test-catalog.md](08-test-catalog.md).
