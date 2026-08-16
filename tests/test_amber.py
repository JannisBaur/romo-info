from __future__ import annotations

from datetime import date, datetime

from romo_bot.amber import AmberAdvisor
from romo_bot.models import TideDirection, TideExtreme, TideForecast, WeatherForecast

_DAYTIME_LOW_TIDE = TideForecast(
    extremes=(
        TideExtreme(at=datetime(2026, 8, 15, 10, 42), height_m=-0.2, direction=TideDirection.LOW),
    )
)
_OVERNIGHT_LOW_TIDE = TideForecast(
    extremes=(
        TideExtreme(at=datetime(2026, 8, 17, 0, 7), height_m=-0.03, direction=TideDirection.LOW),
    )
)
_MIXED_LOW_TIDES = TideForecast(
    extremes=(
        TideExtreme(at=datetime(2026, 8, 17, 0, 7), height_m=-0.03, direction=TideDirection.LOW),
        TideExtreme(at=datetime(2026, 8, 17, 12, 14), height_m=-0.02, direction=TideDirection.LOW),
    )
)
_NO_TIDE = TideForecast(extremes=())


def _weather(
    *, speed_kmh: float, recent_storm: bool, upcoming_storm: date | None = None
) -> WeatherForecast:
    return WeatherForecast(
        day_parts=(),
        temperature_min_c=14.0,
        temperature_max_c=18.0,
        wind_speed_max_kmh=speed_kmh,
        wind_direction_deg=270.0,
        recent_onshore_storm=recent_storm,
        upcoming_storm_date=upcoming_storm,
    )


def test_recent_storm_and_calm_today_is_good_conditions() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "Good conditions" in note
    assert "10:42" in note


def test_recent_storm_but_still_rough_today_says_wait() -> None:
    weather = _weather(speed_kmh=40.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "wait for calmer seas" in note
    assert "40" in note


def test_no_recent_storm_explains_why_todays_wind_does_not_count() -> None:
    weather = _weather(speed_kmh=37.0, recent_storm=False)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "No onshore storm in the past few days" in note
    assert "37" in note


def test_no_low_tide_omits_timing_note() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _NO_TIDE)

    assert "low tide" not in note.lower()


def test_overnight_only_low_tide_is_not_recommended_as_best_time() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _OVERNIGHT_LOW_TIDE)

    assert "Best around low tide" not in note
    assert "overnight" in note.lower()
    assert "00:07" in note


def test_prefers_daytime_low_tide_over_overnight_one() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _MIXED_LOW_TIDES)

    assert "Best around low tide (~12:14)" in note
    assert "00:07" not in note


def test_upcoming_storm_is_mentioned_as_a_heads_up() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=False, upcoming_storm=date(2026, 8, 19))

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "Wed 19 Aug" in note
    assert "storm forecast" in note.lower()


def test_no_upcoming_storm_says_so_explicitly() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=False, upcoming_storm=None)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "No onshore storm forecast" in note
