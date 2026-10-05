"""Escalating N+1 detection: Q(2S) <= Q(S) + k on SELECT count (catalog 08)."""

from __future__ import annotations

from collections.abc import Callable

from django.db import connection
from django.test.utils import CaptureQueriesContext


def count_selects(captured_queries: list[dict]) -> int:
    return sum(
        1
        for q in captured_queries
        if q["sql"].lstrip().upper().startswith("SELECT")
    )


def assert_selects_do_not_grow(
    *,
    call_endpoint: Callable[[], object],
    build_size_s: Callable[[], object],
    build_size_2s: Callable[[], object],
    k: int = 2,
) -> None:
    """Fail if SELECT count grows more than ``k`` when dataset doubles.

    INSERT/UPDATE/BEGIN/COMMIT may grow on writes; only SELECT growth is asserted.
    Requires Django ``DEBUG=True`` (query capture).
    """
    build_size_s()
    with CaptureQueriesContext(connection) as ctx_s:
        call_endpoint()
    q_s = count_selects(ctx_s.captured_queries)

    build_size_2s()
    with CaptureQueriesContext(connection) as ctx_2s:
        call_endpoint()
    q_2s = count_selects(ctx_2s.captured_queries)

    assert q_2s <= q_s + k, (
        f"SELECT query growth detected: Q(S)={q_s}, Q(2S)={q_2s}, allowed k={k}. "
        f"SELECTs(S)={[q['sql'][:120] for q in ctx_s.captured_queries if q['sql'].lstrip().upper().startswith('SELECT')]} "
        f"SELECTs(2S)={[q['sql'][:120] for q in ctx_2s.captured_queries if q['sql'].lstrip().upper().startswith('SELECT')]}"
    )
