from __future__ import annotations

from datetime import date
from typing import Any

import httpx
import pytest
import respx

from romo_info.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)
from romo_info.models import StormOutlook, WeatherForecast

_TODAY = date(2026, 8, 16)
# Matches the client's real days=2, _STORM_LOOKAHEAD_DAYS=5 combination --
# the fixture payload below is shaped for exactly this window.
_DAYS = 2
_FORECAST_DAYS_TOTAL = _DAYS + 5


def _parse(payload: dict[str, Any]) -> tuple[WeatherForecast, WeatherForecast, StormOutlook]:
    (today, tomorrow), outlook = OpenMeteoWeatherClient._parse_response(
        payload, _TODAY, _DAYS, _FORECAST_DAYS_TOTAL
    )
    return today, tomorrow, outlook


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
        "precipitation_probability": [90.0] * 16 + [10.0] * 16 + [70.0] * 16,
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
        "wind_speed_10m_max": [10.0, 12.0, 11.0, 60.0, 20.0, 15.0, 65.0, 14.0, 13.0, 12.0],
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
    route = respx.get(FORECAST_API_URL)
    route.mock(return_value=httpx.Response(500))
    client = OpenMeteoWeatherClient(
        latitude=55.1, longitude=8.5, timezone="UTC", sleep=lambda _seconds: None
    )

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast(1)

    # A 5xx is treated as possibly transient, so all 3 attempts get used.
    assert route.call_count == 3


@respx.mock
def test_client_error_is_not_retried() -> None:
    route = respx.get(FORECAST_API_URL)
    route.mock(return_value=httpx.Response(404))
    client = OpenMeteoWeatherClient(
        latitude=55.1, longitude=8.5, timezone="UTC", sleep=lambda _seconds: None
    )

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast(1)

    # A 4xx won't fix itself on retry, so only one attempt is made.
    assert route.call_count == 1


@respx.mock
def test_transient_connection_error_is_retried() -> None:
    route = respx.get(FORECAST_API_URL)
    route.mock(
        side_effect=[
            httpx.ConnectTimeout("handshake timed out"),
            httpx.Response(200, json={"unexpected": True}),
        ]
    )
    client = OpenMeteoWeatherClient(
        latitude=55.1, longitude=8.5, timezone="UTC", sleep=lambda _seconds: None
    )

    # The second response is a real HTTP reply (just an unexpected shape),
    # which only gets reached if the first ConnectTimeout was retried past.
    with pytest.raises(OpenMeteoClientError, match="Unexpected forecast API response shape"):
        client.fetch_weather_forecast(1)

    assert route.call_count == 2


@respx.mock
def test_server_error_is_retried_then_succeeds() -> None:
    route = respx.get(FORECAST_API_URL)
    route.mock(
        side_effect=[
            httpx.Response(503),
            httpx.Response(200, json={"unexpected": True}),
        ]
    )
    client = OpenMeteoWeatherClient(
        latitude=55.1, longitude=8.5, timezone="UTC", sleep=lambda _seconds: None
    )

    with pytest.raises(OpenMeteoClientError, match="Unexpected forecast API response shape"):
        client.fetch_weather_forecast(1)

    assert route.call_count == 2


@respx.mock
def test_persistent_connection_errors_exhaust_all_attempts() -> None:
    route = respx.get(FORECAST_API_URL)
    route.mock(side_effect=httpx.ConnectTimeout("handshake timed out"))
    sleeps: list[float] = []
    client = OpenMeteoWeatherClient(
        latitude=55.1, longitude=8.5, timezone="UTC", sleep=sleeps.append
    )

    with pytest.raises(OpenMeteoClientError, match="after 3 attempts"):
        client.fetch_weather_forecast(1)

    assert route.call_count == 3
    # Backoff grows between attempts (2s, then 4s) -- no sleep after the
    # final, failed attempt.
    assert sleeps == [2.0, 4.0]


def test_fetch_weather_forecast_returns_todays_and_tomorrows_day_parts() -> None:
    today, tomorrow, _outlook = _parse(_SUCCESS_PAYLOAD)

    assert all(p.summary == "Overcast" and p.temperature_c == 16.0 for p in today.day_parts)
    assert all(p.summary == "Rain showers" and p.temperature_c == 12.0 for p in tomorrow.day_parts)


def test_fetch_weather_forecast_uses_correct_daily_values_per_day() -> None:
    today, tomorrow, _outlook = _parse(_SUCCESS_PAYLOAD)

    assert today.temperature_max_c == 18.0
    assert today.wind_speed_max_kmh == 60.0
    assert tomorrow.temperature_max_c == 15.0
    assert tomorrow.wind_speed_max_kmh == 20.0


def test_storm_on_today_only_counts_as_recent_for_tomorrow() -> None:
    today, tomorrow, _outlook = _parse(_SUCCESS_PAYLOAD)

    assert today.recent_onshore_storm is False
    assert tomorrow.recent_onshore_storm is True


def test_upcoming_storm_beyond_tomorrow_is_flagged_once_for_the_whole_report() -> None:
    _today, _tomorrow, outlook = _parse(_SUCCESS_PAYLOAD)

    assert outlook.upcoming_storm_date == date(2026, 8, 19)


def test_lookback_days_differ_between_today_and_tomorrow() -> None:
    today, tomorrow, _outlook = _parse(_SUCCESS_PAYLOAD)

    # Today looks back over exactly the 3 fetched past days; tomorrow's
    # window is one day longer since today itself counts as "past" for it.
    assert today.recent_storm_lookback_days == 3
    assert tomorrow.recent_storm_lookback_days == 4


def test_lookahead_reaches_the_end_of_the_requested_forecast_window() -> None:
    _today, _tomorrow, outlook = _parse(_SUCCESS_PAYLOAD)

    # forecast_days=7 starting from today (the 16th) reaches through the 22nd.
    assert outlook.lookahead_through == date(2026, 8, 22)


def test_strongest_onshore_wiring_matches_the_qualifying_storm_when_one_exists() -> None:
    # The 16th (60 km/h onshore) is the only onshore day in tomorrow's past
    # window, and the 19th (65 km/h onshore) is the only onshore day in the
    # future window -- both already qualify as full storms, so the
    # "strongest onshore" fields should just point at the same day.
    _today, tomorrow, outlook = _parse(_SUCCESS_PAYLOAD)

    assert tomorrow.recent_strongest_onshore_kmh == 60.0
    assert outlook.strongest_onshore_date == date(2026, 8, 19)
    assert outlook.strongest_onshore_wind_kmh == 65.0


def test_strongest_onshore_is_none_when_no_onshore_wind_in_the_window() -> None:
    # Today's past window (13th-15th) is entirely offshore (due east).
    today, _tomorrow, _outlook = _parse(_SUCCESS_PAYLOAD)

    assert today.recent_strongest_onshore_kmh is None


def test_days_argument_shifts_which_days_count_as_future_outlook() -> None:
    # The 17th is a strong onshore day. With days=2 it's fully reported
    # (not part of the future outlook window), so no upcoming storm is
    # flagged; with days=1, it falls into the future window instead.
    payload = {
        "hourly": {
            "time": [],
            "temperature_2m": [],
            "weathercode": [],
            "precipitation_probability": [],
        },
        "daily": {
            "time": ["2026-08-16", "2026-08-17", "2026-08-18"],
            "temperature_2m_min": [10.0, 10.0, 10.0],
            "temperature_2m_max": [15.0, 15.0, 15.0],
            "wind_speed_10m_max": [10.0, 70.0, 10.0],
            "wind_direction_10m_dominant": [90.0, 250.0, 90.0],
        },
    }

    (_today, _tomorrow), outlook_2_days = OpenMeteoWeatherClient._parse_response(
        payload, date(2026, 8, 16), 2, 2 + 5
    )
    assert outlook_2_days.upcoming_storm_date is None

    (_today_only,), outlook_1_day = OpenMeteoWeatherClient._parse_response(
        payload, date(2026, 8, 16), 1, 1 + 5
    )
    assert outlook_1_day.upcoming_storm_date == date(2026, 8, 17)


def test_forecast_days_request_param_scales_with_days_argument() -> None:
    captured: dict[str, Any] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured.update(request.url.params)
        return httpx.Response(200, json=_SUCCESS_PAYLOAD)

    with respx.mock:
        respx.get(FORECAST_API_URL).mock(side_effect=capture)
        client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")
        client.fetch_weather_forecast(3)

    # 3 fully-reported days + the fixed 5-day storm lookahead.
    assert captured["forecast_days"] == "8"


@respx.mock
def test_fetch_weather_forecast_raises_on_malformed_payload() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast(1)
