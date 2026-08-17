from __future__ import annotations

from typing import Protocol

from romo_info.models import (
    StargazingForecast,
    StormOutlook,
    TideForecast,
    WeatherForecast,
)


class TideDataSource(Protocol):
    def fetch_tide_forecast(self, days: int) -> tuple[TideForecast, ...]:
        """Returns `days` consecutive TideForecast entries, starting today."""
        ...


class WeatherDataSource(Protocol):
    def fetch_weather_forecast(
        self, days: int
    ) -> tuple[tuple[WeatherForecast, ...], StormOutlook, StargazingForecast | None]:
        """Returns (`days` consecutive WeatherForecast entries starting
        today, storm_outlook, tonight's stargazing conditions).
        """
        ...


class ReportPublisher(Protocol):
    def publish(self, html: str) -> None: ...
