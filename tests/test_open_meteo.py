from __future__ import annotations

import httpx
import pytest
import respx

from romo_bot.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)

# past_days=3 means the API returns 4 days of daily data (3 past + today)
# and hourly data spanning all of them too. Yesterday (Aug 15) is given a
# different weathercode (61, rain) than today (3, overcast) specifically
# to catch a bug where past days leak into today's day-part bucketing.
_SUCCESS_PAYLOAD = {
    "hourly": {
        "time": (
            [f"2026-08-15T{hour:02d}:00" for hour in range(6, 22)]
            + [f"2026-08-16T{hour:02d}:00" for hour in range(6, 22)]
        ),
        "temperature_2m": [99.0] * 16 + [16.0] * 16,
        "weathercode": [61] * 16 + [3] * 16,
    },
    "daily": {
        "time": ["2026-08-13", "2026-08-14", "2026-08-15", "2026-08-16"],
        "temperature_2m_min": [8.0, 9.0, 10.0, 12.0],
        "temperature_2m_max": [14.0, 15.0, 16.0, 18.0],
        # A strong onshore blow on the 14th, calm otherwise; today (16th)
        # is a moderate breeze that shouldn't itself count as "the storm".
        "wind_speed_10m_max": [10.0, 50.0, 12.0, 25.0],
        "wind_direction_10m_dominant": [90.0, 250.0, 90.0, 270.0],
    },
}


@respx.mock
def test_fetch_weather_forecast_raises_on_http_error() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(500))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()


@respx.mock
def test_fetch_weather_forecast_uses_only_todays_hours_for_day_parts() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json=_SUCCESS_PAYLOAD))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert [p.label for p in forecast.day_parts] == ["Morning", "Afternoon", "Evening"]
    assert all(p.summary == "Overcast" for p in forecast.day_parts)
    assert all(p.temperature_c == 16.0 for p in forecast.day_parts)


@respx.mock
def test_fetch_weather_forecast_uses_todays_daily_values() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json=_SUCCESS_PAYLOAD))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.temperature_max_c == 18.0
    assert forecast.wind_speed_max_kmh == 25.0
    assert forecast.wind_direction_deg == 270.0


@respx.mock
def test_fetch_weather_forecast_detects_recent_onshore_storm() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json=_SUCCESS_PAYLOAD))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.recent_onshore_storm is True


@respx.mock
def test_fetch_weather_forecast_raises_on_malformed_payload() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()
