from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum


class TideDirection(Enum):
    HIGH = "high"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class TideExtreme:
    at: datetime
    height_m: float
    direction: TideDirection


@dataclass(frozen=True, slots=True)
class TideForecast:
    extremes: tuple[TideExtreme, ...]


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    """Only what the beach actually needs.

    General conditions are left to weather apps, and the amber verdict is
    left to Ravvejr, who model it properly. Wind stays because it decides
    whether the beach is pleasant and which way the sea is being pushed.
    """

    wind_speed_max_kmh: float
    wind_direction_deg: float


@dataclass(frozen=True, slots=True)
class StargazingForecast:
    """Tonight's viewing conditions, sunset through to tomorrow's sunrise.

    Report-wide rather than per-day: "tonight" is one night regardless of
    how many days the page covers.
    """

    darkness_from: datetime
    darkness_to: datetime
    # None when the hourly data doesn't reach across tonight -- reported as
    # unavailable rather than silently passed off as a clear sky.
    cloud_cover_pct: int | None
    moon_illumination_pct: int
    moon_phase: str
    # The least cloudy hour in the window. A mean alone can't tell
    # "hazy all night" from "clear until midnight, then closes in".
    clearest_at: datetime | None
    clearest_cover_pct: int | None


@dataclass(frozen=True, slots=True)
class DayForecast:
    for_date: date
    label: str
    tide: TideForecast
    weather: WeatherForecast
    tide_note: str


@dataclass(frozen=True, slots=True)
class DailyReport:
    report_date: datetime
    days: tuple[DayForecast, ...]
    stargazing_note: str
    # Empty for most of the year -- no listed shower is running, and
    # saying so nightly would be filler.
    meteor_note: str
