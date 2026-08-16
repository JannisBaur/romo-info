from __future__ import annotations

from datetime import datetime

from romo_bot.amber import AmberAdvisor
from romo_bot.models import TideDirection, TideExtreme, TideForecast, WeatherForecast

_LOW_TIDE = TideForecast(
    extremes=(
        TideExtreme(at=datetime(2026, 8, 15, 10, 42), height_m=-0.2, direction=TideDirection.LOW),
    )
)
_NO_TIDE = TideForecast(extremes=())


def _weather(*, speed_kmh: float, recent_storm: bool) -> WeatherForecast:
    return WeatherForecast(
        day_parts=(),
        temperature_min_c=14.0,
        temperature_max_c=18.0,
        wind_speed_max_kmh=speed_kmh,
        wind_direction_deg=270.0,
        recent_onshore_storm=recent_storm,
    )


def test_recent_storm_and_calm_today_is_good_conditions() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "Good conditions" in note
    assert "10:42" in note


def test_recent_storm_but_still_rough_today_says_wait() -> None:
    weather = _weather(speed_kmh=40.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "wait for calmer seas" in note


def test_no_recent_storm_is_unlikely_regardless_of_todays_wind() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=False)

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "No recent storm" in note


def test_no_low_tide_omits_timing_note() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _NO_TIDE)

    assert "low tide" not in note.lower()
