from __future__ import annotations

from dataclasses import dataclass, field

from romo_bot.models import TideForecast, WeatherForecast


@dataclass
class FakeTideSource:
    today: TideForecast
    tomorrow: TideForecast

    def fetch_tide_forecast(self) -> tuple[TideForecast, TideForecast]:
        return self.today, self.tomorrow


@dataclass
class FakeWeatherSource:
    today: WeatherForecast
    tomorrow: WeatherForecast

    def fetch_weather_forecast(self) -> tuple[WeatherForecast, WeatherForecast]:
        return self.today, self.tomorrow


@dataclass
class FakeMessageSender:
    sent: list[tuple[str, str]] = field(default_factory=list)

    def send(self, group_jid: str, text: str) -> None:
        self.sent.append((group_jid, text))


@dataclass
class FailingMessageSender:
    def send(self, group_jid: str, text: str) -> None:
        raise RuntimeError("boom")
