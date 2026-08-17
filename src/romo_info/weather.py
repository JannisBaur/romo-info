from __future__ import annotations

from collections.abc import Sequence
from datetime import date

# Amber washes ashore on Denmark's North Sea coast in a two-phase pattern:
# a storm (classically from the SW) loosens it from the seabed first, then
# it's carried in during the calmer weather that follows. 16 m/s (~58 km/h)
# as the "strong enough to stir the seabed" threshold is corroborated by
# multiple independent Danish amber-hunting sources (ravjagt.dk, ravvejr.dk,
# ravfund.dk), not just one -- see _CALM_ENOUGH_WIND_KMH in amber.py for the
# matching "calm enough afterward" threshold from the same sources.
_STORM_WIND_KMH = 58.0
_ONSHORE_MIN_DEG = 202.5  # SW
_ONSHORE_MAX_DEG = 337.5  # NW -- Rømø's beach faces roughly west

_COMPASS_POINTS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)


def compass_point(degrees: float) -> str:
    """Bearing as a 16-point compass label, e.g. 250 -> "WSW"."""
    return _COMPASS_POINTS[round(degrees / 22.5) % 16]


def is_onshore(degrees: float) -> bool:
    """Whether wind from this bearing blows in off the sea at Rømø.

    Shares its bounds with the storm checks above, so the direction shown
    on the page can't drift out of step with the direction the amber rules
    actually apply.
    """
    return _ONSHORE_MIN_DEG <= degrees <= _ONSHORE_MAX_DEG


def had_recent_onshore_storm(
    daily_wind_speeds_kmh: Sequence[float], daily_wind_directions_deg: Sequence[float]
) -> bool:
    """True if any of the given past days had a strong onshore blow.

    Pass only *past* days (not today) -- this checks whether the seabed was
    recently churned up, not today's conditions.
    """
    if len(daily_wind_speeds_kmh) != len(daily_wind_directions_deg):
        raise ValueError(
            "daily_wind_speeds_kmh and daily_wind_directions_deg must be the same length"
        )
    return any(
        speed >= _STORM_WIND_KMH and _ONSHORE_MIN_DEG <= direction <= _ONSHORE_MAX_DEG
        for speed, direction in zip(daily_wind_speeds_kmh, daily_wind_directions_deg, strict=True)
    )


def next_onshore_storm(
    dates: Sequence[date],
    daily_wind_speeds_kmh: Sequence[float],
    daily_wind_directions_deg: Sequence[float],
) -> date | None:
    """Earliest of the given (future) dates with a strong onshore blow
    forecast, or None if none qualify -- a heads-up for planning ahead,
    since amber is best hunted in the calm that follows a storm like this.
    """
    if not (len(dates) == len(daily_wind_speeds_kmh) == len(daily_wind_directions_deg)):
        raise ValueError(
            "dates, daily_wind_speeds_kmh, and daily_wind_directions_deg must be the same length"
        )
    storm_dates = [
        d
        for d, speed, direction in zip(
            dates, daily_wind_speeds_kmh, daily_wind_directions_deg, strict=True
        )
        if speed >= _STORM_WIND_KMH and _ONSHORE_MIN_DEG <= direction <= _ONSHORE_MAX_DEG
    ]
    return min(storm_dates) if storm_dates else None


def strongest_onshore_day(
    dates: Sequence[date],
    daily_wind_speeds_kmh: Sequence[float],
    daily_wind_directions_deg: Sequence[float],
) -> tuple[date, float] | None:
    """The onshore-direction day with the strongest wind in the given
    window, regardless of whether it clears _STORM_WIND_KMH.

    A hard threshold on its own throws away useful information: a 50 km/h
    onshore blow that just misses the "storm" cutoff isn't nothing -- it
    may be the best chance going. This lets callers mention it instead of
    collapsing "almost a storm" and "dead calm" into the same message.
    Returns None only if no day in the window had onshore wind at all.
    """
    if not (len(dates) == len(daily_wind_speeds_kmh) == len(daily_wind_directions_deg)):
        raise ValueError(
            "dates, daily_wind_speeds_kmh, and daily_wind_directions_deg must be the same length"
        )
    onshore_days = [
        (d, speed)
        for d, speed, direction in zip(
            dates, daily_wind_speeds_kmh, daily_wind_directions_deg, strict=True
        )
        if _ONSHORE_MIN_DEG <= direction <= _ONSHORE_MAX_DEG
    ]
    return max(onshore_days, key=lambda day_and_speed: day_and_speed[1]) if onshore_days else None
