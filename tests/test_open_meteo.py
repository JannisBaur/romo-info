from __future__ import annotations

from contextlib import suppress
from datetime import date
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import pytest
import respx

from romo_info.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)
from romo_info.models import WeatherForecast

_ZONE = ZoneInfo("Europe/Copenhagen")
_TODAY = date(2026, 8, 16)
# Matches the client's real days=2, _STORM_LOOKAHEAD_DAYS=5 combination --
# the fixture payload below is shaped for exactly this window.
_DAYS = 2
_FORECAST_DAYS_TOTAL = _DAYS + 1


def _parse(payload: dict[str, Any]) -> tuple[WeatherForecast, WeatherForecast]:
    (today, tomorrow), _stars = OpenMeteoWeatherClient._parse_response(
        payload, _TODAY, _DAYS, _FORECAST_DAYS_TOTAL, _ZONE
    )
    return today, tomorrow


# past_days=3 + forecast_days=7 means 10 days of daily data (3 past, today,
# tomorrow, and 5 more days ahead) and hourly data spanning them too.
# Yesterday (Aug 15) is given a different weathercode (61, rain) than today
# (3, overcast) and tomorrow (80, showers), specifically to catch a bug
# where one day's hours leak into another's day-part bucketing.
_SUCCESS_PAYLOAD = {
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


def test_fetch_weather_forecast_uses_correct_daily_values_per_day() -> None:
    today, tomorrow = _parse(_SUCCESS_PAYLOAD)

    assert today.wind_speed_max_kmh == 60.0
    assert tomorrow.wind_speed_max_kmh == 20.0


def test_forecast_days_request_param_scales_with_days_argument() -> None:
    captured: dict[str, Any] = {}

    def capture(request: httpx.Request) -> httpx.Response:
        captured.update(request.url.params)
        return httpx.Response(200, json=_SUCCESS_PAYLOAD)

    with respx.mock:
        respx.get(FORECAST_API_URL).mock(side_effect=capture)
        client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")
        # Only the outgoing request matters here. Parsing needs the fixture
        # to span today, which depends on the real clock, so don't make
        # this assertion hostage to what day it is run.
        with suppress(OpenMeteoClientError):
            client.fetch_weather_forecast(3)

    # 3 fully-reported days + one extra so tonight's window can reach
    # tomorrow's sunrise.
    assert captured["forecast_days"] == "4"


@respx.mock
def test_fetch_weather_forecast_raises_on_malformed_payload() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast(1)


# Exactly the shape Open-Meteo returns when a timezone is requested: local
# times with *no* offset. An earlier version parsed these into naive
# datetimes, which the moon calculation rejected -- and because that
# happened inside the client, it took the whole report down rather than
# just the stargazing line.
_TONIGHT_PAYLOAD = {
    "hourly": {
        "time": [f"2026-08-17T{h:02d}:00" for h in range(18, 24)]
        + [f"2026-08-18T{h:02d}:00" for h in range(0, 8)],
        # Overcast up to 21:00, clear from 22:00. Darkness starts 45 min
        # after the 20:54 sunset, so only the clear hours should count.
        "cloud_cover": [80.0] * 4 + [10.0] * 10,
    },
    "daily": {
        "time": ["2026-08-17", "2026-08-18"],
        "wind_speed_10m_max": [20.0, 20.0],
        "wind_direction_10m_dominant": [250.0, 250.0],
        "sunset": ["2026-08-17T20:54", "2026-08-18T20:52"],
        "sunrise": ["2026-08-17T06:10", "2026-08-18T06:12"],
    },
}


def test_tonight_is_parsed_from_naive_local_times() -> None:
    _days, tonight = OpenMeteoWeatherClient._parse_response(
        _TONIGHT_PAYLOAD, date(2026, 8, 17), 1, 1 + 1, _ZONE
    )

    assert tonight is not None
    # Naive input must come back attached to the requested zone, or the
    # moon calculation rejects it.
    assert tonight.darkness_from.tzinfo is not None
    assert tonight.darkness_to.tzinfo is not None
    assert 0 <= tonight.moon_illumination_pct <= 100
    assert tonight.moon_phase


def test_tonight_averages_only_the_dark_hours() -> None:
    _days, tonight = OpenMeteoWeatherClient._parse_response(
        _TONIGHT_PAYLOAD, date(2026, 8, 17), 1, 1 + 1, _ZONE
    )

    assert tonight is not None
    # Darkness starts 45 min after the 20:54 sunset, so the overcast
    # evening hours before that are excluded and it reads clear.
    assert tonight.cloud_cover_pct == 10


def test_a_broken_stargazing_payload_does_not_sink_the_report() -> None:
    # The stargazing note is the least important thing on the page; the
    # tides and amber outlook must survive it failing.
    payload = {
        "hourly": {"time": ["nonsense"], "cloud_cover": [10.0]},
        "daily": {
            "time": ["2026-08-17", "2026-08-18"],
            "wind_speed_10m_max": [20.0, 20.0],
            "wind_direction_10m_dominant": [250.0, 250.0],
            "sunset": ["not-a-time", "2026-08-18T20:52"],
            "sunrise": ["2026-08-17T06:10", "2026-08-18T06:12"],
        },
    }

    days, tonight = OpenMeteoWeatherClient._parse_response(
        payload, date(2026, 8, 17), 1, 1 + 1, _ZONE
    )

    assert tonight is None
    assert len(days) == 1


def test_missing_sun_times_degrade_to_no_stargazing_note() -> None:
    payload = {
        "daily": {
            "time": ["2026-08-17"],
            "wind_speed_10m_max": [20.0],
            "wind_direction_10m_dominant": [250.0],
        },
    }

    _days, tonight = OpenMeteoWeatherClient._parse_response(
        payload, date(2026, 8, 17), 1, 1 + 1, _ZONE
    )

    assert tonight is None
