from __future__ import annotations

import httpx
import pytest
import respx

from romo_bot.clients.open_meteo import (
    FORECAST_API_URL,
    MARINE_API_URL,
    OpenMeteoClientError,
    OpenMeteoTideClient,
    OpenMeteoWeatherClient,
)


@respx.mock
def test_fetch_tide_forecast_parses_extremes() -> None:
    respx.get(MARINE_API_URL).mock(
        return_value=httpx.Response(
            200,
            json={
                "hourly": {
                    "time": ["2026-08-16T00:00", "2026-08-16T01:00", "2026-08-16T02:00"],
                    "sea_level_height_msl": [1.0, 2.0, 1.0],
                }
            },
        )
    )
    client = OpenMeteoTideClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_tide_forecast()

    assert len(forecast.extremes) == 1
    assert forecast.extremes[0].height_m == 2.0


@respx.mock
def test_fetch_tide_forecast_raises_on_http_error() -> None:
    respx.get(MARINE_API_URL).mock(return_value=httpx.Response(500))
    client = OpenMeteoTideClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_tide_forecast()


@respx.mock
def test_fetch_tide_forecast_raises_on_malformed_payload() -> None:
    respx.get(MARINE_API_URL).mock(return_value=httpx.Response(200, json={"unexpected": True}))
    client = OpenMeteoTideClient(latitude=55.1, longitude=8.5, timezone="UTC")

    with pytest.raises(OpenMeteoClientError):
        client.fetch_tide_forecast()


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
                }
            },
        )
    )
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.summary == "Overcast"
    assert forecast.temperature_max_c == 18.0
    assert forecast.wind_speed_max_kmh == 25.0


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
                }
            },
        )
    )
    client = OpenMeteoWeatherClient(latitude=55.1, longitude=8.5, timezone="UTC")

    forecast = client.fetch_weather_forecast()

    assert forecast.summary == "Unknown conditions"
