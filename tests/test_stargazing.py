from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from romo_info.models import StargazingForecast
from romo_info.stargazing import (
    build_forecast,
    describe,
    mean_cloud_cover,
    moon_illumination_fraction,
    moon_phase_name,
    night_window,
)


def _at(year: int, month: int, day: int, hour: int = 0) -> datetime:
    return datetime(year, month, day, hour, tzinfo=UTC)


def test_known_new_moon_is_dark() -> None:
    # 2026-01-18 was a new moon.
    assert moon_illumination_fraction(_at(2026, 1, 18, 20)) < 0.03


def test_known_full_moon_is_lit() -> None:
    # 2026-01-03 was a full moon.
    assert moon_illumination_fraction(_at(2026, 1, 3, 10)) > 0.97


def test_illumination_stays_within_bounds_across_a_full_cycle() -> None:
    start = _at(2026, 3, 1)
    values = [moon_illumination_fraction(start + timedelta(hours=h)) for h in range(0, 720, 6)]

    assert all(0.0 <= v <= 1.0 for v in values)
    # A full synodic month must contain both a dark and a full moon.
    assert min(values) < 0.02
    assert max(values) > 0.98


def test_naive_datetime_is_rejected() -> None:
    with pytest.raises(ValueError, match="aware datetime"):
        moon_illumination_fraction(datetime(2026, 1, 18, 20))


def test_phase_names_match_the_known_moons() -> None:
    assert moon_phase_name(_at(2026, 1, 18, 20)) == "new moon"
    assert moon_phase_name(_at(2026, 1, 3, 10)) == "full moon"


def test_mean_cloud_cover_only_counts_hours_inside_the_window() -> None:
    timestamps = [_at(2026, 8, 17, h) for h in range(18, 24)]
    covers = [90.0, 90.0, 10.0, 10.0, 10.0, 10.0]

    # Window starts at 20:00, so the two overcast evening hours are excluded.
    mean = mean_cloud_cover(timestamps, covers, _at(2026, 8, 17, 20), _at(2026, 8, 17, 23))

    assert mean == pytest.approx(10.0)


def test_mean_cloud_cover_returns_none_when_the_window_is_not_covered() -> None:
    timestamps = [_at(2026, 8, 17, h) for h in range(6, 12)]
    covers = [10.0] * 6

    assert mean_cloud_cover(timestamps, covers, _at(2026, 8, 18, 22), _at(2026, 8, 19, 4)) is None


def test_mean_cloud_cover_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        mean_cloud_cover([_at(2026, 8, 17, 20)], [10.0, 20.0], _at(2026, 8, 17), _at(2026, 8, 18))


def test_night_window_trims_twilight_from_both_ends() -> None:
    sunset = _at(2026, 8, 17, 21)
    sunrise = _at(2026, 8, 18, 6)

    start, end = night_window(sunset, sunrise)

    assert start > sunset
    assert end < sunrise


def _forecast(*, cloud: int | None, moon: int) -> StargazingForecast:
    return StargazingForecast(
        darkness_from=_at(2026, 8, 17, 22),
        darkness_to=_at(2026, 8, 18, 5),
        cloud_cover_pct=cloud,
        moon_illumination_pct=moon,
        moon_phase="waxing crescent",
    )


def test_clear_dark_night_reads_as_good() -> None:
    assert "good" in describe(_forecast(cloud=10, moon=5))


def test_clear_but_moonlit_night_is_caveated_not_condemned() -> None:
    # A bright moon doesn't stop you seeing planets, so it's a caveat.
    note = describe(_forecast(cloud=10, moon=95))

    assert "wash out" in note
    assert "good" not in note


def test_overcast_night_says_so() -> None:
    assert "clouded out" in describe(_forecast(cloud=90, moon=5))


def test_missing_cloud_data_is_reported_not_guessed() -> None:
    assert "unavailable" in describe(_forecast(cloud=None, moon=5))
    assert "unavailable" in describe(None)


def test_build_forecast_judges_the_moon_mid_night() -> None:
    timestamps = [_at(2026, 8, 17, 22), _at(2026, 8, 17, 23)]
    forecast = build_forecast(
        darkness_from=_at(2026, 8, 17, 22),
        darkness_to=_at(2026, 8, 17, 23),
        timestamps=timestamps,
        cloud_cover_pct=[20.0, 40.0],
    )

    assert forecast.cloud_cover_pct == 30
    assert 0 <= forecast.moon_illumination_pct <= 100
