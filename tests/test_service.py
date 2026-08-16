from __future__ import annotations

from datetime import date

import pytest

from romo_bot.amber import AmberAdvisor
from romo_bot.models import DayPartForecast, TideForecast, WeatherForecast
from romo_bot.report import ReportFormatter
from romo_bot.service import DailyReportService
from tests.fakes import FailingMessageSender, FakeMessageSender, FakeTideSource, FakeWeatherSource

_TODAY_WEATHER = WeatherForecast(
    day_parts=(DayPartForecast(label="Morning", summary="Sunny", temperature_c=12.0),),
    temperature_min_c=10.0,
    temperature_max_c=15.0,
    wind_speed_max_kmh=10.0,
    wind_direction_deg=270.0,
    recent_onshore_storm=True,
    recent_storm_lookback_days=3,
    upcoming_storm_date=None,
    storm_lookahead_through=date(2026, 8, 22),
)
_TOMORROW_WEATHER = WeatherForecast(
    day_parts=(DayPartForecast(label="Morning", summary="Cloudy", temperature_c=11.0),),
    temperature_min_c=9.0,
    temperature_max_c=13.0,
    wind_speed_max_kmh=15.0,
    wind_direction_deg=200.0,
    recent_onshore_storm=False,
    recent_storm_lookback_days=4,
    upcoming_storm_date=None,
    storm_lookahead_through=date(2026, 8, 22),
)


def _service(sender: FakeMessageSender | FailingMessageSender) -> DailyReportService:
    return DailyReportService(
        tide_source=FakeTideSource(TideForecast(extremes=()), TideForecast(extremes=())),
        weather_source=FakeWeatherSource(_TODAY_WEATHER, _TOMORROW_WEATHER),
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


def test_run_includes_both_days() -> None:
    sender = FakeMessageSender()
    _service(sender).run()

    _, text = sender.sent[0]
    assert "Today" in text
    assert "Tomorrow" in text
    assert "Sunny" in text
    assert "Cloudy" in text


def test_run_includes_amber_note_from_advisor() -> None:
    sender = FakeMessageSender()
    _service(sender).run()

    _, text = sender.sent[0]
    assert "Amber hunting" in text


def test_run_propagates_sender_failures() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        _service(FailingMessageSender()).run()
