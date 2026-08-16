from __future__ import annotations

import httpx
import pytest
import respx

from romo_bot.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)

_SUCCESS_PAYLOAD = {
    "hourly": {
        "time": [f"2026-08-16T{hour:02d}:00" for hour in range(6, 22)],
        "temperature_2m": [16.0] * 16,
        "weathercode": [3] * 16,
    },
    "daily": {
        "temperature_2m_min": [12.0],
        "temperature_2m_max": [18.0],
        "wind_speed_10m_max": [25.0],
        "wind_direction_10m_dominant": [270.0],
    },
}


@respx.mock
def test_fetch_weather_forecast_raises_on_http_error() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(500))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()


@respx.mock
def test_fetch_weather_forecast_parses_day_parts_and_daily_summary() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json=_SUCCESS_PAYLOAD))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert [p.label for p in forecast.day_parts] == ["Morning", "Afternoon", "Evening"]
    assert all(p.summary == "Overcast" for p in forecast.day_parts)
    assert forecast.temperature_max_c == 18.0
    assert forecast.wind_speed_max_kmh == 25.0
    assert forecast.wind_direction_deg == 270.0


@respx.mock
def test_fetch_weather_forecast_raises_on_malformed_payload() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()
