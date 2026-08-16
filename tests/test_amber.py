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


def _weather(*, speed_kmh: float, direction_deg: float) -> WeatherForecast:
    return WeatherForecast(
        day_parts=(),
        temperature_min_c=14.0,
        temperature_max_c=18.0,
        wind_speed_max_kmh=speed_kmh,
        wind_direction_deg=direction_deg,
    )


def test_strong_onshore_wind_is_good_conditions() -> None:
    weather = _weather(speed_kmh=30.0, direction_deg=270.0)  # due west, onshore

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "Good conditions" in note
    assert "30" in note
    assert "10:42" in note


def test_strong_offshore_wind_is_less_likely() -> None:
    weather = _weather(speed_kmh=30.0, direction_deg=90.0)  # due east, offshore

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "not onshore" in note


def test_calm_wind_is_unlikely() -> None:
    weather = _weather(speed_kmh=10.0, direction_deg=270.0)

    note = AmberAdvisor().suggest(weather, _LOW_TIDE)

    assert "Calm conditions" in note


def test_no_low_tide_omits_timing_note() -> None:
    weather = _weather(speed_kmh=30.0, direction_deg=270.0)

    note = AmberAdvisor().suggest(weather, _NO_TIDE)

    assert "low tide" not in note.lower()
