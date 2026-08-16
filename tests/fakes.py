from __future__ import annotations

from dataclasses import dataclass, field

from romo_bot.models import TideForecast, WeatherForecast


@dataclass
class FakeTideSource:
    forecast: TideForecast

    def fetch_tide_forecast(self) -> TideForecast:
        return self.forecast


@dataclass
class FakeWeatherSource:
    forecast: WeatherForecast

    def fetch_weather_forecast(self) -> WeatherForecast:
        return self.forecast


@dataclass
class FakeMessageSender:
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, group_jid: str, text: str) -> None:
        self.sent.append((group_jid, text))


@dataclass
class FailingMessageSender:
    def send(self, group_jid: str, text: str) -> None:
        raise RuntimeError("boom")
