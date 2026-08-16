from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from romo_bot.models import TideDirection, TideExtreme


def find_tide_extremes(
    timestamps: Sequence[datetime], heights_m: Sequence[float]
) -> tuple[TideExtreme, ...]:
    """Locate local high/low points in an hourly sea-level series.

    Pure function: given the same inputs it always returns the same output,
    so it is tested directly with fixed data, no network required.
    """
    if len(timestamps) != len(heights_m):
        raise ValueError("timestamps and heights_m must be the same length")

    extremes: list[TideExtreme] = []
    for i in range(1, len(heights_m) - 1):
        previous, current, following = heights_m[i - 1], heights_m[i], heights_m[i + 1]
        if current > previous and current > following:
            extremes.append(TideExtreme(timestamps[i], current, TideDirection.HIGH))
        elif current < previous and current < following:
            extremes.append(TideExtreme(timestamps[i], current, TideDirection.LOW))
    return tuple(extremes)
