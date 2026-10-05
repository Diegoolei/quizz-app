"""Scoring helpers — `.cursor/specs/03-attempts-and-scoring.md`."""

from __future__ import annotations


def score_percent(correct_count: int, total_count: int) -> int:
    """Return ``round(100 * correct_count / total_count)`` (Python 3 ``round``).

    Raises:
        ValueError: when ``total_count`` is zero.
    """
    if total_count == 0:
        raise ValueError("total_count must be > 0")
    return round(100 * correct_count / total_count)


def performance_message_for(score_percent: int) -> str:
    """Map score percent to normative performance band message."""
    if score_percent < 40:
        return "Keep practicing"
    if score_percent < 70:
        return "Nice effort"
    if score_percent < 90:
        return "Great job"
    return "Excellent"
