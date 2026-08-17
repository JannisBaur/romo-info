from __future__ import annotations

import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from romo_info.models import StargazingForecast, StormOutlook, WeatherForecast
from romo_info.stargazing import build_forecast, night_window
from romo_info.weather import (
    had_recent_onshore_storm,
    next_onshore_storm,
    strongest_onshore_day,
)

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# How many days back to look for a storm that could have loosened amber
# from the seabed (see weather.had_recent_onshore_storm).
_PAST_DAYS_FOR_STORM_CHECK = 3
# Extra days of just-wind data fetched beyond the last fully-reported day,
# to spot an upcoming onshore storm worth planning around (see
# weather.next_onshore_storm). Open-Meteo's own forecast skill drops off
# well before this horizon, so this is a heads-up, not a promise. Fixed
# regardless of how many days are fully reported -- that's a separate,
# caller-supplied concern (see fetch_weather_forecast's `days` argument).
_STORM_LOOKAHEAD_DAYS = 5

# This runs unattended once a day via cron -- a single dropped connection
# (DNS hiccup, a timed-out TLS handshake) shouldn't cost the day's report.
# Retried: connection-level failures (timeouts, DNS, reset) and 5xx server
# errors, since both are plausibly transient. Not retried: 4xx errors,
# since retrying a bad request just wastes the remaining attempts.
_MAX_ATTEMPTS = 3
_RETRY_BACKOFF_SECONDS = 2.0


class OpenMeteoClientError(RuntimeError):
    """Raised when an Open-Meteo request fails or returns unexpected data."""


class OpenMeteoWeatherClient:
    """Fetches daily wind and tonight's cloud cover from Open-Meteo.

    Wind covers the requested reported days plus the days before
    (recent-storm check) and after (upcoming-storm heads-up) that the amber
    outlook needs. The only hourly series requested is cloud cover, for the
    stargazing note -- general conditions are left to ordinary weather apps.
    """

    def __init__(
        self,
        latitude: float,
        longitude: float,
        timezone: str,
        *,
        client: httpx.Client | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._latitude = latitude
        self._longitude = longitude
        self._timezone = timezone
        self._client = client or httpx.Client(timeout=10.0)
        self._sleep = sleep

    def fetch_weather_forecast(
        self, days: int
    ) -> tuple[tuple[WeatherForecast, ...], StormOutlook, StargazingForecast | None]:
        forecast_days_total = days + _STORM_LOOKAHEAD_DAYS
        response = self._get_with_retries(forecast_days_total)
        try:
            today_date = datetime.now(ZoneInfo(self._timezone)).date()
            return self._parse_response(response.json(), today_date, days, forecast_days_total)
        except (KeyError, TypeError, ValueError, IndexError) as exc:
            raise OpenMeteoClientError(f"Unexpected forecast API response shape: {exc}") from exc

    def _get_with_retries(self, forecast_days_total: int) -> httpx.Response:
        params: dict[str, str | float | int] = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            # Hourly cloud cover is only for the stargazing note; general
            # conditions are deliberately not reported (see README).
            "hourly": "cloud_cover",
            "daily": "wind_speed_10m_max,wind_direction_10m_dominant,sunset,sunrise",
            "timezone": self._timezone,
            "forecast_days": forecast_days_total,
            "past_days": _PAST_DAYS_FOR_STORM_CHECK,
        }
        attempt = 0
        while True:
            attempt += 1
            is_last_attempt = attempt >= _MAX_ATTEMPTS
            try:
                response = self._client.get(FORECAST_API_URL, params=params)
                response.raise_for_status()
                return response
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or is_last_attempt:
                    raise OpenMeteoClientError(f"Forecast API request failed: {exc}") from exc
            except httpx.TransportError as exc:
                if is_last_attempt:
                    raise OpenMeteoClientError(
                        f"Forecast API request failed after {_MAX_ATTEMPTS} attempts: {exc}"
                    ) from exc
            self._sleep(_RETRY_BACKOFF_SECONDS * attempt)

    @staticmethod
    def _parse_response(
        payload: dict[str, Any], today_date: date, days: int, forecast_days_total: int
    ) -> tuple[tuple[WeatherForecast, ...], StormOutlook, StargazingForecast | None]:
        daily = payload["daily"]
        daily_dates = [date.fromisoformat(d) for d in daily["time"]]
        wind_speeds = [float(s) for s in daily["wind_speed_10m_max"]]
        wind_directions = [float(d) for d in daily["wind_direction_10m_dominant"]]

        # today_date is identified independently from wall-clock time
        # (matching the requested timezone) rather than by array position
        # -- robust regardless of exactly how past_days/forecast_days line
        # up, and keeps this method pure/testable given a fixed date.
        last_reported_date = today_date + timedelta(days=days - 1)

        future_indices = [i for i, d in enumerate(daily_dates) if d > last_reported_date]
        future_dates = [daily_dates[i] for i in future_indices]
        future_speeds = [wind_speeds[i] for i in future_indices]
        future_directions = [wind_directions[i] for i in future_indices]
        upcoming_storm_date = next_onshore_storm(future_dates, future_speeds, future_directions)
        strongest_upcoming = strongest_onshore_day(future_dates, future_speeds, future_directions)
        storm_outlook = StormOutlook(
            upcoming_storm_date=upcoming_storm_date,
            lookahead_through=today_date + timedelta(days=forecast_days_total - 1),
            strongest_onshore_date=strongest_upcoming[0] if strongest_upcoming else None,
            strongest_onshore_wind_kmh=strongest_upcoming[1] if strongest_upcoming else None,
        )

        def forecast_for(target_date: date) -> WeatherForecast:
            day_index = daily_dates.index(target_date)
            # "Past" here means before *this* day -- a later reported day's
            # lookback naturally includes the earlier reported days too,
            # since those count as part of its recent past.
            past_indices = [i for i, d in enumerate(daily_dates) if d < target_date]
            past_dates = [daily_dates[i] for i in past_indices]
            past_speeds = [wind_speeds[i] for i in past_indices]
            past_directions = [wind_directions[i] for i in past_indices]
            strongest_recent = strongest_onshore_day(past_dates, past_speeds, past_directions)
            return WeatherForecast(
                wind_speed_max_kmh=wind_speeds[day_index],
                wind_direction_deg=wind_directions[day_index],
                recent_onshore_storm=had_recent_onshore_storm(past_speeds, past_directions),
                recent_storm_lookback_days=len(past_indices),
                recent_strongest_onshore_kmh=(strongest_recent[1] if strongest_recent else None),
                recent_strongest_onshore_date=(strongest_recent[0] if strongest_recent else None),
            )

        reported = tuple(
            forecast_for(today_date + timedelta(days=offset)) for offset in range(days)
        )
        return reported, storm_outlook, _parse_tonight(payload, daily_dates, today_date)


def _parse_tonight(
    payload: dict[str, Any], daily_dates: list[date], today_date: date
) -> StargazingForecast | None:
    """Tonight's stargazing conditions: today's sunset to tomorrow's sunrise.

    Returns None rather than raising if the window falls outside the data
    -- a missing stargazing note shouldn't cost the rest of the report.
    """
    daily = payload["daily"]
    try:
        today_index = daily_dates.index(today_date)
        sunset = datetime.fromisoformat(daily["sunset"][today_index])
        next_sunrise = datetime.fromisoformat(daily["sunrise"][today_index + 1])
    except (KeyError, ValueError, IndexError):
        return None

    hourly = payload.get("hourly", {})
    timestamps = [datetime.fromisoformat(t) for t in hourly.get("time", [])]
    # Open-Meteo sends null past its horizon; treat those hours as absent
    # rather than as clear sky.
    covers = [float(c) for c in hourly.get("cloud_cover", []) if c is not None]
    if len(covers) != len(timestamps):
        timestamps, covers = [], []

    darkness_from, darkness_to = night_window(sunset, next_sunrise)
    return build_forecast(
        darkness_from=darkness_from,
        darkness_to=darkness_to,
        timestamps=timestamps,
        cloud_cover_pct=covers,
    )
