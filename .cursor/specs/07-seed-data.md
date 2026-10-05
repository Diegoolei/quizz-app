# 07 — Seed data

## Summary

Preload content so a fresh environment can exercise the API without manual quiz authoring.

## Requirements

- At least **2 quizzes**.
- Each seeded quiz has at least **5 questions**.
- Each question: ≥ 2 options, exactly one correct, non-empty explanation.
- Topic: AI development concepts (aligned with product goal).
- Deterministic ids/slugs optional; titles must be stable for docs/demos.

## Delivery mechanism

- Django data migration and/or `manage.py` management command (`seed_quizzes`) invoked from docs/entrypoint as appropriate.
- Seeding must be idempotent (re-run does not duplicate quizzes — match on stable title or seed key).

## Users

- Seed users are optional. Acceptance does not require preloaded users; clients create via API.

## Tests

Catalog: `D-SEED` in [08-test-catalog.md](08-test-catalog.md).

- `api/tests/test_seed_data.py` — ≥2 quizzes, each ≥5 questions; single-correct invariant; idempotent re-run
