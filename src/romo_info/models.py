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

    General conditions (temperature, cloud, chance of rain) used to be
    reported here too, but any weather app does that better, and a single
    number summarising a six-hour window was repeatedly misleading. Wind
    stays because it drives the amber outlook and decides whether the
    beach is pleasant.
    """

    wind_speed_max_kmh: float
    # Dominant direction the wind blows *from*, in degrees. Amber-relevant
    # in its own right: an onshore blow pushes loosened amber towards the
    # beach, an offshore one of the same strength does not.
    wind_direction_deg: float
    recent_onshore_storm: bool
    recent_storm_lookback_days: int
    # The strongest onshore-direction day in the lookback window, even if it
    # didn't clear the full "storm" threshold -- None only if there was no
    # onshore wind at all. Lets the amber note mention a near-miss blow
    # instead of a threshold silently discarding it. The date rides along
    # because "there was a 32 km/h blow" is not actionable without knowing
    # whether it was yesterday or three days ago.
    recent_strongest_onshore_kmh: float | None
    recent_strongest_onshore_date: date | None


@dataclass(frozen=True, slots=True)
class StormOutlook:
    """A single, report-wide look-ahead -- not per-day, since "is a storm
    coming in the next few days" doesn't depend on whether you're reading
    today's or tomorrow's section.
    """

    upcoming_storm_date: date | None
    lookahead_through: date
    # Strongest onshore-direction day in the lookahead window, even if it
    # never reaches full "storm" strength -- same reasoning as
    # WeatherForecast.recent_strongest_onshore_kmh above, applied forward
    # instead of backward. None only if no day in the window had onshore
    # wind at all.
    strongest_onshore_date: date | None
    strongest_onshore_wind_kmh: float | None


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
    storm_outlook_note: str
