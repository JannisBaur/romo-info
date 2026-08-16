from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from romo_bot.models import StormOutlook, TideForecast, WeatherForecast

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

    def fetch_weather_forecast(self, days: int) -> tuple[tuple[WeatherForecast, ...], StormOutlook]:
        return (self.today, self.tomorrow)[:days], self.outlook


@dataclass
class FakeMessageSender:
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, group_jid: str, text: str) -> None:
        self.sent.append((group_jid, text))


@dataclass
class FailingMessageSender:
    def send(self, group_jid: str, text: str) -> None:
        raise RuntimeError("boom")
