from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from romo_bot.models import DayPartForecast

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


def bucket_day_parts(
    timestamps: Sequence[datetime],
    temperatures_c: Sequence[float],
    weather_codes: Sequence[int],
) -> tuple[DayPartForecast, ...]:
    """Groups hourly weather into Morning/Afternoon/Evening summaries.

    Pure function: given the same hourly readings it always returns the
    same day-part breakdown, so it's tested directly with fixed input, no
    network or mocking needed.
    """
    if not (len(timestamps) == len(temperatures_c) == len(weather_codes)):
        raise ValueError("timestamps, temperatures_c, and weather_codes must be the same length")

    parts: list[DayPartForecast] = []
    for label, start_hour, end_hour in _DAY_PARTS:
        indices = [i for i, at in enumerate(timestamps) if start_hour <= at.hour < end_hour]
        if not indices:
            continue
        average_temp = sum(temperatures_c[i] for i in indices) / len(indices)
        # The most severe code in the window is the more useful headline
        # (e.g. one rainy hour in an otherwise clear morning still means
        # "bring a jacket"); WMO codes increase with severity.
        worst_code = max(weather_codes[i] for i in indices)
        parts.append(
            DayPartForecast(
                label=label,
                summary=WEATHER_CODE_SUMMARIES.get(worst_code, "Unknown conditions"),
                temperature_c=average_temp,
            )
        )
    return tuple(parts)
