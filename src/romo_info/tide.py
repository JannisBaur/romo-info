from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from romo_info.models import TideDirection, TideExtreme, TideForecast


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


_REASONABLE_HOUR_START = 6
_REASONABLE_HOUR_END = 21


def falling_tide_note(tide: TideForecast) -> str:
    """When the water is on its way out, which is when to walk the beach.

    Danish guidance is to start on the falling water and work down as
    fresh ground is exposed, rather than to arrive at low water -- that
    instant is only the bottom of the window.
    """
    low_tides = [e for e in tide.extremes if e.direction == TideDirection.LOW]
    if not low_tides:
        return ""

    daytime_lows = [
        e for e in low_tides if _REASONABLE_HOUR_START <= e.at.hour < _REASONABLE_HOUR_END
    ]
    if not daytime_lows:
        # Every low that day is overnight -- say so rather than implying
        # it's a sensible time to be on the beach.
        overnight = min(low_tides, key=lambda e: e.at)
        return f"Water is only fully out overnight (~{overnight.at:%H:%M})."

    best = min(daytime_lows, key=lambda e: e.at)
    preceding_high = max(
        (e for e in tide.extremes if e.direction == TideDirection.HIGH and e.at < best.at),
        key=lambda e: e.at,
        default=None,
    )
    if preceding_high is not None:
        return (
            f"Falling tide from ~{preceding_high.at:%H:%M}" f" down to low water ~{best.at:%H:%M}."
        )
    # The fall began before midnight, so this day's extremes don't carry
    # its start -- name what we do know.
    return f"Falling tide down to low water ~{best.at:%H:%M}."
