from __future__ import annotations

import httpx
import pytest
import respx

from romo_bot.clients.open_meteo import (
    FORECAST_API_URL,
    OpenMeteoClientError,
    OpenMeteoWeatherClient,
)


@respx.mock
def test_fetch_weather_forecast_raises_on_http_error() -> None:
    respx.get(FORECAST_API_URL).mock(return_value=httpx.Response(500))
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_weather_forecast()


@respx.mock
def test_fetch_weather_forecast_parses_daily_summary() -> None:
    respx.get(FORECAST_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "daily": {
                    "weathercode": [3],
                    "temperature_2m_min": [12.0],
                    "temperature_2m_max": [18.0],
                    "wind_speed_10m_max": [25.0],
                    "wind_direction_10m_dominant": [270.0],
                }
            },
        )
    )
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.summary == "Overcast"
    assert forecast.temperature_max_c == 18.0
    assert forecast.wind_speed_max_kmh == 25.0
    assert forecast.wind_direction_deg == 270.0


@respx.mock
def test_fetch_weather_forecast_unknown_code_falls_back() -> None:
    respx.get(FORECAST_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "daily": {
                    "weathercode": [999],
                    "temperature_2m_min": [12.0],
                    "temperature_2m_max": [18.0],
                    "wind_speed_10m_max": [25.0],
                    "wind_direction_10m_dominant": [270.0],
                }
            },
        )
    )
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.summary == "Unknown conditions"
