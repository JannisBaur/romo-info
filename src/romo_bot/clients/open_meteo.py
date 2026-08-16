from __future__ import annotations

from datetime import date, datetime
from typing import Any

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
    """Fetches today's and tomorrow's weather (by day part) from Open-Meteo's
    Forecast API, plus the past few days' wind (for the amber-hunting storm
    check).
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

    def fetch_weather_forecast(self) -> tuple[WeatherForecast, WeatherForecast]:
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
                "forecast_days": 2,
                "past_days": _PAST_DAYS_FOR_STORM_CHECK,
            },
        )
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise OpenMeteoClientError(f"Forecast API request failed: {exc}") from exc

        try:
            return self._parse_response(response.json())
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoClientError(f"Unexpected forecast API response shape: {exc}") from exc

    @staticmethod
    def _parse_response(payload: dict[str, Any]) -> tuple[WeatherForecast, WeatherForecast]:
        hourly = payload["hourly"]
        all_timestamps = [datetime.fromisoformat(t) for t in hourly["time"]]
        all_temperatures = [float(t) for t in hourly["temperature_2m"]]
        all_codes = [int(c) for c in hourly["weathercode"]]

        daily = payload["daily"]
        daily_dates = [date.fromisoformat(d) for d in daily["time"]]
        wind_speeds = [float(s) for s in daily["wind_speed_10m_max"]]
        wind_directions = [float(d) for d in daily["wind_direction_10m_dominant"]]
        temperature_mins = [float(t) for t in daily["temperature_2m_min"]]
        temperature_maxs = [float(t) for t in daily["temperature_2m_max"]]

        # past_days puts earlier days first, forecast days last -- the two
        # latest dates present are today and tomorrow.
        sorted_dates = sorted(daily_dates)
        today_date, tomorrow_date = sorted_dates[-2], sorted_dates[-1]

        def forecast_for(target_date: date) -> WeatherForecast:
            hour_indices = [i for i, t in enumerate(all_timestamps) if t.date() == target_date]
            day_parts = bucket_day_parts(
                [all_timestamps[i] for i in hour_indices],
                [all_temperatures[i] for i in hour_indices],
                [all_codes[i] for i in hour_indices],
            )
            day_index = daily_dates.index(target_date)
            # "Past" here means before *this* day -- for tomorrow's storm
            # check, today itself counts as part of the recent past.
            past_indices = [i for i, d in enumerate(daily_dates) if d < target_date]
            return WeatherForecast(
                day_parts=day_parts,
                temperature_min_c=temperature_mins[day_index],
                temperature_max_c=temperature_maxs[day_index],
                wind_speed_max_kmh=wind_speeds[day_index],
                wind_direction_deg=wind_directions[day_index],
                recent_onshore_storm=had_recent_onshore_storm(
                    [wind_speeds[i] for i in past_indices],
                    [wind_directions[i] for i in past_indices],
                ),
            )

        return forecast_for(today_date), forecast_for(tomorrow_date)
