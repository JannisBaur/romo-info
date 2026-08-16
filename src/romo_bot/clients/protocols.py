from __future__ import annotations

from typing import Protocol

from romo_bot.models import StormOutlook, TideForecast, WeatherForecast


class TideDataSource(Protocol):
    def fetch_tide_forecast(self, days: int) -> tuple[TideForecast, ...]:
        """Returns `days` consecutive TideForecast entries, starting today."""
        ...


class WeatherDataSource(Protocol):
    def fetch_weather_forecast(self, days: int) -> tuple[tuple[WeatherForecast, ...], StormOutlook]:
        """Returns (`days` consecutive WeatherForecast entries starting
        today, storm_outlook).
        """
        ...


class MessageSender(Protocol):
    def send(self, group_jid: str, text: str) -> None: ...
