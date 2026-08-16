from __future__ import annotations

import httpx

from romo_bot.models import WeatherForecast

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# Open-Meteo's weathercode -> short human summary (WMO code table, common subset).
_WEATHER_CODE_SUMMARIES: dict[int, str] = {
    0: "Clear sky",
    1: "Mostly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    80: "Rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    95: "Thunderstorm",
}


class OpenMeteoClientError(RuntimeError):
    """Raised when an Open-Meteo request fails or returns unexpected data."""


class OpenMeteoWeatherClient:
    """Fetches today's weather summary from Open-Meteo's Forecast API."""

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
                "daily": (
                    "weathercode,temperature_2m_max,temperature_2m_min,"
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
            daily = response.json()["daily"]
            code = int(daily["weathercode"][0])
            return WeatherForecast(
                summary=_WEATHER_CODE_SUMMARIES.get(code, "Unknown conditions"),
                temperature_min_c=float(daily["temperature_2m_min"][0]),
                temperature_max_c=float(daily["temperature_2m_max"][0]),
                wind_speed_max_kmh=float(daily["wind_speed_10m_max"][0]),
                wind_direction_deg=float(daily["wind_direction_10m_dominant"][0]),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoClientError(f"Unexpected forecast API response shape: {exc}") from exc
