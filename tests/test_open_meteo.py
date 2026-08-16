from __future__ import annotations

from datetime import date

import httpx
import pytest
import respx

from romo_bot.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)

_TODAY = date(2026, 8, 16)

# past_days=3 + forecast_days=7 means 10 days of daily data (3 past, today,
# tomorrow, and 5 more days ahead) and hourly data spanning them too.
# Yesterday (Aug 15) is given a different weathercode (61, rain) than today
# (3, overcast) and tomorrow (80, showers), specifically to catch a bug
# where one day's hours leak into another's day-part bucketing.
_SUCCESS_PAYLOAD = {
    "hourly": {
        "time": (
            [f"2026-08-15T{hour:02d}:00" for hour in range(6, 22)]
            + [f"2026-08-16T{hour:02d}:00" for hour in range(6, 22)]
            + [f"2026-08-17T{hour:02d}:00" for hour in range(6, 22)]
        ),
        "temperature_2m": [99.0] * 16 + [16.0] * 16 + [12.0] * 16,
        "weathercode": [61] * 16 + [3] * 16 + [80] * 16,
    },
    "daily": {
        "time": [
            "2026-08-13",
            "2026-08-14",
            "2026-08-15",
            "2026-08-16",  # today
            "2026-08-17",  # tomorrow
            "2026-08-18",
            "2026-08-19",  # the upcoming storm
            "2026-08-20",
            "2026-08-21",
            "2026-08-22",
        ],
        "temperature_2m_min": [8.0, 9.0, 10.0, 12.0, 11.0, 10.0, 9.0, 11.0, 12.0, 13.0],
        "temperature_2m_max": [14.0, 15.0, 16.0, 18.0, 15.0, 14.0, 13.0, 16.0, 17.0, 18.0],
        # Calm on the 13th-15th; a strong onshore blow ON today (the 16th)
        # itself -- this should NOT count as "recent" for today (it's
        # today, not the past), but SHOULD count for tomorrow (the 17th),
        # since today counts as "past" relative to tomorrow. Then calm
        # again until a strong onshore blow forecast for the 19th, which
        # should surface as an upcoming-storm heads-up for both days.
        "wind_speed_10m_max": [10.0, 12.0, 11.0, 50.0, 20.0, 15.0, 55.0, 14.0, 13.0, 12.0],
        "wind_direction_10m_dominant": [
            90.0,
            90.0,
            90.0,
            250.0,
            200.0,
            90.0,
            260.0,
            90.0,
            90.0,
            90.0,
        ],
    },
}


@respx.mock
def test_fetch_weather_forecast_raises_on_http_error() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(500))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()


def test_fetch_weather_forecast_returns_todays_and_tomorrows_day_parts() -> None:
    today, tomorrow = OpenMeteoWeatherClient._parse_response(_SUCCESS_PAYLOAD, _TODAY)

    assert all(p.summary == "Overcast" and p.temperature_c == 16.0 for p in today.day_parts)
    assert all(p.summary == "Rain showers" and p.temperature_c == 12.0 for p in tomorrow.day_parts)


def test_fetch_weather_forecast_uses_correct_daily_values_per_day() -> None:
    today, tomorrow = OpenMeteoWeatherClient._parse_response(_SUCCESS_PAYLOAD, _TODAY)

    assert today.temperature_max_c == 18.0
    assert today.wind_speed_max_kmh == 50.0
    assert tomorrow.temperature_max_c == 15.0
    assert tomorrow.wind_speed_max_kmh == 20.0


def test_storm_on_today_only_counts_as_recent_for_tomorrow() -> None:
    today, tomorrow = OpenMeteoWeatherClient._parse_response(_SUCCESS_PAYLOAD, _TODAY)

    assert today.recent_onshore_storm is False
    assert tomorrow.recent_onshore_storm is True


def test_upcoming_storm_beyond_tomorrow_is_flagged_for_both_days() -> None:
    today, tomorrow = OpenMeteoWeatherClient._parse_response(_SUCCESS_PAYLOAD, _TODAY)

    assert today.upcoming_storm_date == date(2026, 8, 19)
    assert tomorrow.upcoming_storm_date == date(2026, 8, 19)


@respx.mock
def test_fetch_weather_forecast_raises_on_malformed_payload() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()
