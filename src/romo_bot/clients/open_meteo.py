from __future__ import annotations

from datetime import datetime

import httpx

from romo_bot.models import WeatherForecast
from romo_bot.weather import bucket_day_parts

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"


class OpenMeteoClientError(RuntimeError):
    """Raised when an Open-Meteo request fails or returns unexpected data."""


class OpenMeteoWeatherClient:
    """Fetches today's weather (by day part) from Open-Meteo's Forecast API."""

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        *,
        client: httpx.Client | None = None,
    ) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._timezone = timezone
        self._client = client or httpx.Client(timeout=10.0)

    def fetch_weather_forecast(self) -> WeatherForecast:
        response = self._client.get(
            FORECAST_API_URL,
            params={
                "latitude": self._latitude,
                "longitude": self._longitude,
                "hourly": "temperature_2m,weathercode",
                "daily": (
                    "temperature_2m_max,temperature_2m_min,"
                    "wind_speed_10m_max,wind_direction_10m_dominant"
                ),
                "timezone": self._timezone,
                "forecast_days": 1,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OpenMeteoClientError(f"Forecast API request failed: {exc}") from exc

        try:
            payload = response.json()
            hourly = payload["hourly"]
            timestamps = [datetime.fromisoformat(t) for t in hourly["time"]]
            temperatures_c = [float(t) for t in hourly["temperature_2m"]]
            weather_codes = [int(c) for c in hourly["weathercode"]]
            day_parts = bucket_day_parts(timestamps, temperatures_c, weather_codes)

            daily = payload["daily"]
            return WeatherForecast(
                day_parts=day_parts,
                temperature_min_c=float(daily["temperature_2m_min"][0]),
                temperature_max_c=float(daily["temperature_2m_max"][0]),
                wind_speed_max_kmh=float(daily["wind_speed_10m_max"][0]),
                wind_direction_deg=float(daily["wind_direction_10m_dominant"][0]),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoClientError(f"Unexpected forecast API response shape: {exc}") from exc
