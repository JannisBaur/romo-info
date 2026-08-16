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
class DayPartForecast:
    label: str
    summary: str
    temperature_c: float


@dataclass(frozen=True, slots=True)
class WeatherForecast:
    day_parts: tuple[DayPartForecast, ...]
    temperature_min_c: float
    temperature_max_c: float
    wind_speed_max_kmh: float
    wind_direction_deg: float
    recent_onshore_storm: bool
    upcoming_storm_date: date | None


@dataclass(frozen=True, slots=True)
class DayForecast:
    for_date: date
    label: str
    tide: TideForecast
    weather: WeatherForecast
    amber_note: str


@dataclass(frozen=True, slots=True)
class DailyReport:
    report_date: datetime
    days: tuple[DayForecast, ...]
