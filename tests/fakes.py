from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from romo_info.models import (
    StargazingForecast,
    StormOutlook,
    TideForecast,
    WeatherForecast,
)

_DEFAULT_OUTLOOK = StormOutlook(
    upcoming_storm_date=None,
    lookahead_through=date(2026, 8, 22),
    strongest_onshore_date=None,
    strongest_onshore_wind_kmh=None,
)


@dataclass
class FakeTideSource:
    today: TideForecast
    tomorrow: TideForecast

    def fetch_tide_forecast(self, days: int) -> tuple[TideForecast, ...]:
        return (self.today, self.tomorrow)[:days]


@dataclass
class FakeWeatherSource:
    today: WeatherForecast
    tomorrow: WeatherForecast
    outlook: StormOutlook = field(default_factory=lambda: _DEFAULT_OUTLOOK)

    stargazing: StargazingForecast | None = None

    def fetch_weather_forecast(
        self, days: int
    ) -> tuple[tuple[WeatherForecast, ...], StormOutlook, StargazingForecast | None]:
        return (self.today, self.tomorrow)[:days], self.outlook, self.stargazing


@dataclass
class FakeReportPublisher:
    published: list[str] = field(default_factory=list)

    def publish(self, html: str) -> None:
        self.published.append(html)


@dataclass
class FailingReportPublisher:
    def publish(self, html: str) -> None:
        raise RuntimeError("boom")
