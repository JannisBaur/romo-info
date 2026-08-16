from __future__ import annotations

from typing import Protocol

from romo_bot.models import TideForecast, WeatherForecast


class TideDataSource(Protocol):
    def fetch_tide_forecast(self) -> tuple[TideForecast, TideForecast]:
        """Returns (today, tomorrow)."""
        ...


class WeatherDataSource(Protocol):
    def fetch_weather_forecast(self) -> tuple[WeatherForecast, WeatherForecast]:
        """Returns (today, tomorrow)."""
        ...


class MessageSender(Protocol):
    def send(self, group_jid: str, text: str) -> None: ...
