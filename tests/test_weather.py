from __future__ import annotations

from datetime import date, datetime

import pytest

from romo_info.weather import (
    bucket_day_parts,
    had_recent_onshore_storm,
    next_onshore_storm,
    strongest_onshore_day,
)


def _hourly_range(start_hour: int, end_hour: int) -> list[datetime]:
    return [datetime(2026, 8, 16, hour) for hour in range(start_hour, end_hour)]


def test_buckets_hours_into_labelled_day_parts() -> None:
    timestamps = _hourly_range(0, 24)
    temperatures = [10.0] * 24
    codes = [0] * 24  # clear sky throughout

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 24)

    assert [p.label for p in parts] == ["Morning", "Afternoon", "Evening"]
    assert all(p.summary == "Clear sky" for p in parts)


def test_averages_temperature_within_a_day_part() -> None:
    timestamps = _hourly_range(6, 12)
    temperatures = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    codes = [0] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 6)

    assert len(parts) == 1
    assert parts[0].label == "Morning"
    assert parts[0].temperature_c == pytest.approx(15.0)


def test_one_bad_hour_does_not_relabel_an_otherwise_clear_window() -> None:
    # Regression: picking the *most severe* code let a single drizzly hour
    # report the whole afternoon as "Light drizzle", which read as a wet
    # day when the forecast was mostly clear.
    timestamps = _hourly_range(12, 18)
    temperatures = [18.0] * 6
    codes = [0, 0, 51, 0, 0, 0]  # one drizzly hour amid clear sky

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 6)

    assert parts[0].summary == "Clear sky"


def test_dominant_code_wins_when_the_window_is_genuinely_wet() -> None:
    timestamps = _hourly_range(12, 18)
    temperatures = [18.0] * 6
    codes = [61, 61, 61, 61, 0, 0]  # actually a rainy afternoon

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 6)

    assert parts[0].summary == "Slight rain"


def test_tied_conditions_break_toward_the_more_severe_code() -> None:
    timestamps = _hourly_range(12, 18)
    temperatures = [18.0] * 6
    codes = [0, 0, 0, 61, 61, 61]  # half clear, half rain

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 6)

    assert parts[0].summary == "Slight rain"


def test_precipitation_probability_averages_the_window() -> None:
    timestamps = _hourly_range(6, 12)
    temperatures = [10.0] * 6
    codes = [0] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes, [10.0, 10.0, 20.0, 20.0, 30.0, 30.0])

    assert parts[0].precipitation_probability_pct == 20


def test_one_spiky_hour_does_not_set_the_windows_rain_chance() -> None:
    # Regression: taking the highest hour reported a mostly-dry afternoon
    # as "65%" because a single hour peaked there.
    timestamps = _hourly_range(12, 18)
    temperatures = [18.0] * 6
    codes = [2] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes, [10.0, 10.0, 65.0, 10.0, 5.0, 5.0])

    assert parts[0].precipitation_probability_pct == 18


def test_hours_outside_any_window_are_ignored() -> None:
    timestamps = _hourly_range(0, 6)  # entirely before "Morning" starts at 6
    temperatures = [5.0] * 6
    codes = [0] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes, [0.0] * 6)

    assert parts == ()


def test_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        bucket_day_parts(_hourly_range(6, 12), [10.0], [0], [0.0])


def test_strong_onshore_day_counts_as_recent_storm() -> None:
    # Three past days: calm, then a strong SW blow, then calm again.
    speeds = [10.0, 60.0, 12.0]
    directions = [90.0, 250.0, 90.0]

    assert had_recent_onshore_storm(speeds, directions) is True


def test_strong_but_offshore_day_does_not_count() -> None:
    speeds = [10.0, 60.0, 12.0]
    directions = [90.0, 90.0, 90.0]  # strong, but due east -- offshore

    assert had_recent_onshore_storm(speeds, directions) is False


def test_onshore_but_weak_day_does_not_count() -> None:
    speeds = [10.0, 20.0, 12.0]
    directions = [90.0, 250.0, 90.0]  # onshore direction, but not strong enough

    assert had_recent_onshore_storm(speeds, directions) is False


def test_no_days_means_no_storm() -> None:
    assert had_recent_onshore_storm([], []) is False


def test_recent_onshore_storm_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        had_recent_onshore_storm([50.0, 10.0], [250.0])


def test_next_onshore_storm_finds_earliest_qualifying_date() -> None:
    dates = [date(2026, 8, 18), date(2026, 8, 19), date(2026, 8, 20)]
    speeds = [10.0, 60.0, 65.0]  # both the 19th and 20th qualify
    directions = [90.0, 250.0, 260.0]

    assert next_onshore_storm(dates, speeds, directions) == date(2026, 8, 19)


def test_next_onshore_storm_returns_none_when_nothing_qualifies() -> None:
    dates = [date(2026, 8, 18), date(2026, 8, 19)]
    speeds = [10.0, 12.0]
    directions = [90.0, 90.0]

    assert next_onshore_storm(dates, speeds, directions) is None


def test_next_onshore_storm_empty_input_returns_none() -> None:
    assert next_onshore_storm([], [], []) is None


def test_next_onshore_storm_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        next_onshore_storm([date(2026, 8, 18)], [50.0, 10.0], [250.0])


def test_strongest_onshore_day_picks_the_highest_speed_onshore_day() -> None:
    dates = [date(2026, 8, 18), date(2026, 8, 19), date(2026, 8, 20)]
    speeds = [30.0, 50.0, 40.0]  # none reach the full-storm threshold
    directions = [250.0, 260.0, 90.0]  # the 20th is offshore, excluded

    assert strongest_onshore_day(dates, speeds, directions) == (date(2026, 8, 19), 50.0)


def test_strongest_onshore_day_ignores_offshore_days_regardless_of_speed() -> None:
    dates = [date(2026, 8, 18), date(2026, 8, 19)]
    speeds = [70.0, 20.0]
    directions = [90.0, 250.0]  # the strong day is offshore, so the weaker onshore day wins

    assert strongest_onshore_day(dates, speeds, directions) == (date(2026, 8, 19), 20.0)


def test_strongest_onshore_day_returns_none_when_nothing_is_onshore() -> None:
    dates = [date(2026, 8, 18), date(2026, 8, 19)]
    speeds = [30.0, 40.0]
    directions = [90.0, 90.0]

    assert strongest_onshore_day(dates, speeds, directions) is None


def test_strongest_onshore_day_empty_input_returns_none() -> None:
    assert strongest_onshore_day([], [], []) is None


def test_strongest_onshore_day_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        strongest_onshore_day([date(2026, 8, 18)], [50.0, 10.0], [250.0])
