"""D-MSG-bounds — performance message bands (03-attempts-and-scoring)."""

import pytest


@pytest.mark.parametrize(
    ("percent", "message"),
    [
        (0, "Keep practicing"),
        (39, "Keep practicing"),
        (40, "Nice effort"),
        (69, "Nice effort"),
        (70, "Great job"),
        (89, "Great job"),
        (90, "Excellent"),
        (100, "Excellent"),
    ],
)
def test_performance_message_bands(percent, message):
    """Bands: 0–39 Keep practicing; 40–69 Nice effort; 70–89 Great job; 90–100 Excellent."""
    from attempts.services.scoring import performance_message_for

    assert performance_message_for(percent) == message
