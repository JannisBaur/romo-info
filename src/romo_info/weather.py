from __future__ import annotations

from collections import Counter
from collections.abc import Sequence
from datetime import date, datetime

from romo_info.models import DayPartForecast

# Open-Meteo's weathercode -> short human summary (WMO code table, common subset).
WEATHER_CODE_SUMMARIES: dict[int, str] = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}

# (label, start_hour_inclusive, end_hour_exclusive)
_DAY_PARTS: tuple[tuple[str, int, int], ...] = (
    ("Morning", 6, 12),
    ("Afternoon", 12, 18),
    ("Evening", 18, 22),
)

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


def bucket_day_parts(
    timestamps: Sequence[datetime],
    temperatures_c: Sequence[float],
    weather_codes: Sequence[int],
    precipitation_probabilities_pct: Sequence[float],
) -> tuple[DayPartForecast, ...]:
    """Groups hourly weather into Morning/Afternoon/Evening summaries.

    Pure function: given the same hourly readings it always returns the
    same day-part breakdown, so it's tested directly with fixed input, no
    network or mocking needed.
    """
    if not (
        len(timestamps)
        == len(temperatures_c)
        == len(weather_codes)
        == len(precipitation_probabilities_pct)
    ):
        raise ValueError(
            "timestamps, temperatures_c, weather_codes, and "
            "precipitation_probabilities_pct must be the same length"
        )

    parts: list[DayPartForecast] = []
    for label, start_hour, end_hour in _DAY_PARTS:
        indices = [i for i, at in enumerate(timestamps) if start_hour <= at.hour < end_hour]
        if not indices:
            continue
        average_temp = sum(temperatures_c[i] for i in indices) / len(indices)
        parts.append(
            DayPartForecast(
                label=label,
                summary=WEATHER_CODE_SUMMARIES.get(
                    _dominant_code([weather_codes[i] for i in indices]), "Unknown conditions"
                ),
                temperature_c=average_temp,
                precipitation_probability_pct=round(
                    sum(precipitation_probabilities_pct[i] for i in indices) / len(indices)
                ),
            )
        )
    return tuple(parts)


def _dominant_code(codes: Sequence[int]) -> int:
    """The condition that best describes the window as a whole.

    Deliberately *not* the most severe code: taking the max let a single
    drizzly hour label an otherwise clear afternoon "Light drizzle", badly
    overstating the day. The chance of rain is now reported separately
    (precipitation_probability_pct), so choosing the representative
    condition here no longer hides an iffy hour. Ties break toward the
    more severe code, since WMO codes broadly increase with severity.
    """
    counts = Counter(codes)
    most_common_count = max(counts.values())
    return max(code for code, count in counts.items() if count == most_common_count)
