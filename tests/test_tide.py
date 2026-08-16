from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from romo_info.models import TideDirection
from romo_info.tide import find_tide_extremes


def _hours(n: int) -> list[datetime]:
    start = datetime(2026, 8, 16, 0, 0)
    return [start + timedelta(hours=i) for i in range(n)]


def test_finds_high_then_low_in_order() -> None:
    heights = [1.0, 2.0, 1.5, 0.5, 1.0]
    extremes = find_tide_extremes(_hours(len(heights)), heights)
    assert [e.direction for e in extremes] == [TideDirection.HIGH, TideDirection.LOW]
    assert extremes[0].height_m == 2.0
    assert extremes[1].height_m == 0.5


def test_monotonic_series_has_no_extremes() -> None:
    heights = [1.0, 1.5, 2.0, 2.5]
    assert find_tide_extremes(_hours(len(heights)), heights) == ()


def test_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        find_tide_extremes(_hours(3), [1.0, 2.0])
