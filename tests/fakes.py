from __future__ import annotations

from dataclasses import dataclass, field

from romo_info.models import (
    StargazingForecast,
    TideForecast,
    WeatherForecast,
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

    stargazing: StargazingForecast | None = None

    def fetch_weather_forecast(
        self, days: int
    ) -> tuple[tuple[WeatherForecast, ...], StargazingForecast | None]:
        return (self.today, self.tomorrow)[:days], self.stargazing


@dataclass
class FakeReportPublisher:
    published: list[str] = field(default_factory=list)

    def publish(self, html: str) -> None:
        self.published.append(html)


@dataclass
class FailingReportPublisher:
    def publish(self, html: str) -> None:
        raise RuntimeError("boom")
