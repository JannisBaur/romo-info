from __future__ import annotations

import pytest

from romo_bot.amber import AmberAdvisor
from romo_bot.models import DayPartForecast, TideForecast, WeatherForecast
from romo_bot.report import ReportFormatter
from romo_bot.service import DailyReportService
from tests.fakes import FailingMessageSender, FakeMessageSender, FakeTideSource, FakeWeatherSource

_WEATHER = WeatherForecast(
    day_parts=(DayPartForecast(label="Morning", summary="Sunny", temperature_c=12.0),),
    temperature_min_c=10.0,
    temperature_max_c=15.0,
    wind_speed_max_kmh=10.0,
    wind_direction_deg=270.0,
    recent_onshore_storm=True,
)


def _service(sender: FakeMessageSender | FailingMessageSender) -> DailyReportService:
    return DailyReportService(
        tide_source=FakeTideSource(TideForecast(extremes=())),
        weather_source=FakeWeatherSource(_WEATHER),
        sender=sender,
        formatter=ReportFormatter(),
        amber_advisor=AmberAdvisor(),
        group_jid="123@g.us",
        timezone="UTC",
    )


def test_run_sends_formatted_report_to_configured_group() -> None:
    sender = FakeMessageSender()
    _service(sender).run()

    assert len(sender.sent) == 1
    jid, text = sender.sent[0]
    assert jid == "123@g.us"
    assert "Sunny" in text


def test_run_includes_amber_note_from_advisor() -> None:
    sender = FakeMessageSender()
    _service(sender).run()

    _, text = sender.sent[0]
    assert "Amber hunting" in text


def test_run_propagates_sender_failures() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        _service(FailingMessageSender()).run()
