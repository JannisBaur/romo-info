from __future__ import annotations

from datetime import datetime

import pytest

from romo_bot.weather import bucket_day_parts


def _hourly_range(start_hour: int, end_hour: int) -> list[datetime]:
    return [datetime(2026, 8, 16, hour) for hour in range(start_hour, end_hour)]


def test_buckets_hours_into_labelled_day_parts() -> None:
    timestamps = _hourly_range(0, 24)
    temperatures = [10.0] * 24
    codes = [0] * 24  # clear sky throughout

    parts = bucket_day_parts(timestamps, temperatures, codes)

    assert [p.label for p in parts] == ["Morning", "Afternoon", "Evening"]
    assert all(p.summary == "Clear sky" for p in parts)


def test_averages_temperature_within_a_day_part() -> None:
    timestamps = _hourly_range(6, 12)
    temperatures = [10.0, 12.0, 14.0, 16.0, 18.0, 20.0]
    codes = [0] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes)

    assert len(parts) == 1
    assert parts[0].label == "Morning"
    assert parts[0].temperature_c == pytest.approx(15.0)


def test_most_severe_code_in_window_wins() -> None:
    timestamps = _hourly_range(12, 18)
    temperatures = [18.0] * 6
    codes = [0, 0, 61, 0, 0, 0]  # one hour of rain amid clear sky

    parts = bucket_day_parts(timestamps, temperatures, codes)

    assert parts[0].summary == "Slight rain"


def test_hours_outside_any_window_are_ignored() -> None:
    timestamps = _hourly_range(0, 6)  # entirely before "Morning" starts at 6
    temperatures = [5.0] * 6
    codes = [0] * 6

    parts = bucket_day_parts(timestamps, temperatures, codes)

    assert parts == ()


def test_mismatched_lengths_raise_value_error() -> None:
    with pytest.raises(ValueError, match="same length"):
        bucket_day_parts(_hourly_range(6, 12), [10.0], [0])
