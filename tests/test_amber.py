from __future__ import annotations

from datetime import date, datetime

from romo_info.amber import AmberAdvisor
from romo_info.models import (
    StormOutlook,
    TideDirection,
    TideExtreme,
    TideForecast,
    WeatherForecast,
)

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
    *,
    speed_kmh: float,
    recent_storm: bool,
    lookback_days: int = 3,
    strongest_onshore_kmh: float | None = None,
    strongest_onshore_date: date | None = None,
    direction_deg: float = 270.0,
) -> WeatherForecast:
    return WeatherForecast(
        wind_speed_max_kmh=speed_kmh,
        wind_direction_deg=direction_deg,
        recent_onshore_storm=recent_storm,
        recent_storm_lookback_days=lookback_days,
        recent_strongest_onshore_kmh=strongest_onshore_kmh,
        recent_strongest_onshore_date=strongest_onshore_date,
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


def test_near_miss_onshore_blow_is_mentioned_instead_of_hidden() -> None:
    # A 50 km/h onshore blow that misses the full-storm threshold isn't
    # nothing -- it may be the best chance going, so it shouldn't read
    # identically to a day with no onshore wind at all.
    weather = _weather(
        speed_kmh=20.0, recent_storm=False, lookback_days=3, strongest_onshore_kmh=50.0
    )

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "still possible" in note
    assert "50" in note


def test_no_recent_storm_explains_why_todays_wind_does_not_count() -> None:
    weather = _weather(speed_kmh=37.0, recent_storm=False, lookback_days=3)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "No onshore wind at all in the past 3 days" in note
    assert "37" in note


def test_no_low_tide_omits_timing_note() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _NO_TIDE)

    assert "low tide" not in note.lower()


def test_overnight_only_low_tide_is_not_recommended_as_best_time() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _OVERNIGHT_LOW_TIDE)

    assert "falling tide" not in note.lower()
    assert "overnight" in note.lower()
    assert "00:07" in note


def test_prefers_daytime_low_tide_over_overnight_one() -> None:
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _MIXED_LOW_TIDES)

    assert "Best on the falling tide, low water ~12:14" in note
    assert "00:07" not in note


def test_suggest_never_mentions_upcoming_storm() -> None:
    # The per-day verdict only looks backward (has a storm already
    # happened?) -- the forward-looking outlook is a separate, report-wide
    # concern handled by describe_outlook(), not duplicated here.
    weather = _weather(speed_kmh=15.0, recent_storm=True)

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "storm forecast" not in note.lower()
    assert "\n" not in note


def test_describe_outlook_names_the_upcoming_storm() -> None:
    outlook = StormOutlook(
        upcoming_storm_date=date(2026, 8, 19),
        lookahead_through=date(2026, 8, 22),
        strongest_onshore_date=date(2026, 8, 19),
        strongest_onshore_wind_kmh=70.0,
    )

    note = AmberAdvisor.describe_outlook(outlook)

    assert "Wed 19 Aug" in note
    assert "Storm forecast" in note


def test_describe_outlook_mentions_near_miss_when_no_full_storm_qualifies() -> None:
    # A 50 km/h onshore day that misses the full-storm threshold shouldn't
    # read identically to a completely calm week -- it may be the best
    # chance in the window.
    outlook = StormOutlook(
        upcoming_storm_date=None,
        lookahead_through=date(2026, 8, 22),
        strongest_onshore_date=date(2026, 8, 20),
        strongest_onshore_wind_kmh=50.0,
    )

    note = AmberAdvisor.describe_outlook(outlook)

    assert "No full storm forecast through Sat 22 Aug" in note
    assert "Thu 20 Aug" in note
    assert "50" in note


def test_describe_outlook_names_the_date_checked_through_when_nothing_onshore_at_all() -> None:
    outlook = StormOutlook(
        upcoming_storm_date=None,
        lookahead_through=date(2026, 8, 22),
        strongest_onshore_date=None,
        strongest_onshore_wind_kmh=None,
    )

    note = AmberAdvisor.describe_outlook(outlook)

    assert "No storm forecast through Sat 22 Aug" in note


def test_near_miss_blow_says_which_day_it_was() -> None:
    # "there was a 32 km/h blow" is not actionable without knowing whether
    # that was yesterday or three days ago.
    weather = _weather(
        speed_kmh=20.0,
        recent_storm=False,
        strongest_onshore_kmh=32.0,
        strongest_onshore_date=date(2026, 8, 15),
    )

    note = AmberAdvisor().suggest(weather, _DAYTIME_LOW_TIDE)

    assert "32 km/h onshore blow on Sat 15 Aug" in note
