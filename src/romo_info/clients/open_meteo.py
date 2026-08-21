from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from romo_info.models import StargazingForecast, WeatherForecast
from romo_info.stargazing import build_forecast, night_window

logger = logging.getLogger(__name__)

FORECAST_API_URL = "https://api.open-meteo.com/v1/forecast"

# One extra day so tonight's window can reach tomorrow's sunrise.
_EXTRA_DAYS = 1

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

    The only hourly series requested is cloud cover, for the stargazing
    note; general conditions are left to ordinary weather apps.
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
    ) -> tuple[tuple[WeatherForecast, ...], StargazingForecast | None]:
        forecast_days_total = days + _EXTRA_DAYS
        response = self._get_with_retries(forecast_days_total)
        try:
            zone = ZoneInfo(self._timezone)
            today_date = datetime.now(zone).date()
            return self._parse_response(
                response.json(), today_date, days, forecast_days_total, zone
            )
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
        payload: dict[str, Any],
        today_date: date,
        days: int,
        forecast_days_total: int,
        zone: ZoneInfo,
    ) -> tuple[tuple[WeatherForecast, ...], StargazingForecast | None]:
        daily = payload["daily"]
        daily_dates = [date.fromisoformat(d) for d in daily["time"]]
        wind_speeds = [float(s) for s in daily["wind_speed_10m_max"]]
        wind_directions = [float(d) for d in daily["wind_direction_10m_dominant"]]

        # today_date is identified independently from wall-clock time
        # (matching the requested timezone) rather than by array position,
        # which keeps this method pure and testable given a fixed date.
        def forecast_for(target_date: date) -> WeatherForecast:
            day_index = daily_dates.index(target_date)
            return WeatherForecast(
                wind_speed_max_kmh=wind_speeds[day_index],
                wind_direction_deg=wind_directions[day_index],
            )

        reported = tuple(
            forecast_for(today_date + timedelta(days=offset)) for offset in range(days)
        )
        return reported, _parse_tonight(payload, daily_dates, today_date, zone)


def _parse_tonight(
    payload: dict[str, Any], daily_dates: list[date], today_date: date, zone: ZoneInfo
) -> StargazingForecast | None:
    """Tonight's stargazing conditions: today's sunset to tomorrow's sunrise.

    Returns None instead of raising on anything unexpected. The stargazing
    note is the least important thing on the page, and it must never be
    able to take the tides and the amber outlook down with it.

    Open-Meteo returns times as *naive* local strings when a timezone is
    requested, so everything here is attached to `zone` before use -- the
    moon calculation needs an aware datetime, and the hourly stamps have to
    be comparable with the night window.
    """
    try:
        daily = payload["daily"]
        today_index = daily_dates.index(today_date)
        sunset = datetime.fromisoformat(daily["sunset"][today_index]).replace(tzinfo=zone)
        next_sunrise = datetime.fromisoformat(daily["sunrise"][today_index + 1]).replace(
            tzinfo=zone
        )

        hourly = payload.get("hourly", {})
        raw_times = hourly.get("time", [])
        raw_covers = hourly.get("cloud_cover", [])
        # Open-Meteo sends null past its horizon; drop those hours in step
        # so the two series stay aligned, rather than treating a missing
        # reading as clear sky.
        pairs = [
            (datetime.fromisoformat(t).replace(tzinfo=zone), float(c))
            for t, c in zip(raw_times, raw_covers, strict=False)
            if c is not None
        ]
        timestamps = [t for t, _ in pairs]
        covers = [c for _, c in pairs]

        darkness_from, darkness_to = night_window(sunset, next_sunrise)
        return build_forecast(
            darkness_from=darkness_from,
            darkness_to=darkness_to,
            timestamps=timestamps,
            cloud_cover_pct=covers,
        )
    except (KeyError, TypeError, ValueError, IndexError):
        logger.warning("Could not build tonight's stargazing forecast", exc_info=True)
        return None
