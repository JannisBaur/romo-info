from __future__ import annotations

from datetime import date, datetime

import httpx

from romo_bot.models import WeatherForecast
from romo_bot.weather import bucket_day_parts, had_recent_onshore_storm

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# How many days back to look for a storm that could have loosened amber
# from the seabed (see weather.had_recent_onshore_storm).
_PAST_DAYS_FOR_STORM_CHECK = 3


class OpenMeteoClientError(RuntimeError):
    """Raised when an Open-Meteo request fails or returns unexpected data."""


class OpenMeteoWeatherClient:
    """Fetches today's weather (by day part) from Open-Meteo's Forecast API,
    plus the past few days' wind (for the amber-hunting storm check).
    """

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
                "past_days": _PAST_DAYS_FOR_STORM_CHECK,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OpenMeteoClientError(f"Forecast API request failed: {exc}") from exc

        try:
            payload = response.json()

            # past_days extends the hourly series backward too, so filter
            # down to just the most recent (today's) date before bucketing
            # -- else e.g. yesterday's 09:00 and today's 09:00 would both
            # land in "Morning".
            hourly = payload["hourly"]
            all_timestamps = [datetime.fromisoformat(t) for t in hourly["time"]]
            all_temperatures = [float(t) for t in hourly["temperature_2m"]]
            all_codes = [int(c) for c in hourly["weathercode"]]
            today = max(t.date() for t in all_timestamps)
            todays_hours = [i for i, t in enumerate(all_timestamps) if t.date() == today]
            day_parts = bucket_day_parts(
                [all_timestamps[i] for i in todays_hours],
                [all_temperatures[i] for i in todays_hours],
                [all_codes[i] for i in todays_hours],
            )

            daily = payload["daily"]
            daily_dates = [date.fromisoformat(d) for d in daily["time"]]
            today_index = daily_dates.index(max(daily_dates))
            wind_speeds = [float(s) for s in daily["wind_speed_10m_max"]]
            wind_directions = [float(d) for d in daily["wind_direction_10m_dominant"]]
            past_wind_speeds = [s for i, s in enumerate(wind_speeds) if i != today_index]
            past_wind_directions = [d for i, d in enumerate(wind_directions) if i != today_index]

            return WeatherForecast(
                day_parts=day_parts,
                temperature_min_c=float(daily["temperature_2m_min"][today_index]),
                temperature_max_c=float(daily["temperature_2m_max"][today_index]),
                wind_speed_max_kmh=wind_speeds[today_index],
                wind_direction_deg=wind_directions[today_index],
                recent_onshore_storm=had_recent_onshore_storm(
                    past_wind_speeds, past_wind_directions
                ),
            )
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoClientError(f"Unexpected forecast API response shape: {exc}") from exc
