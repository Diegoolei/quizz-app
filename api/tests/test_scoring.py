"""D-SCORE-* — scoring formula (03-attempts-and-scoring / catalog 08)."""

import pytest


@pytest.mark.parametrize(
    ("correct", "total", "expected"),
    [
        (0, 5, 0),
        (1, 5, 20),
        (4, 5, 80),
        (5, 5, 100),
        (1, 3, 33),  # Python 3 round(100 * 1/3) == 33
        (2, 3, 67),
    ],
)
def test_score_percent(correct, total, expected):
    """Per attempt: score_percent = round(100 * correct_count / total_count) via Python 3 round."""
    from attempts.services.scoring import score_percent

    assert score_percent(correct, total) == expected


def test_score_percent_rejects_zero_total():
    from attempts.services.scoring import score_percent

    with pytest.raises(ValueError):
        score_percent(0, 0)
