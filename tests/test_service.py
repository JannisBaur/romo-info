from __future__ import annotations

from datetime import date

import pytest

from romo_info.amber import AmberAdvisor
from romo_info.models import DayPartForecast, StormOutlook, TideForecast, WeatherForecast
from romo_info.report import ReportFormatter
from romo_info.service import DailyReportService, _label_for
from tests.fakes import (
    FailingReportPublisher,
    FakeReportPublisher,
    FakeTideSource,
    FakeWeatherSource,
)

_TODAY_WEATHER = WeatherForecast(
    day_parts=(DayPartForecast(label="Morning", summary="Sunny", temperature_c=12.0),),
    temperature_min_c=10.0,
    temperature_max_c=15.0,
    wind_speed_max_kmh=10.0,
    wind_direction_deg=270.0,
    recent_onshore_storm=True,
    recent_storm_lookback_days=3,
    recent_strongest_onshore_kmh=60.0,
)
_TOMORROW_WEATHER = WeatherForecast(
    day_parts=(DayPartForecast(label="Morning", summary="Cloudy", temperature_c=11.0),),
    temperature_min_c=9.0,
    temperature_max_c=13.0,
    wind_speed_max_kmh=15.0,
    wind_direction_deg=200.0,
    recent_onshore_storm=False,
    recent_storm_lookback_days=4,
    recent_strongest_onshore_kmh=None,
)
_OUTLOOK = StormOutlook(
    upcoming_storm_date=date(2026, 8, 19),
    lookahead_through=date(2026, 8, 22),
    strongest_onshore_date=date(2026, 8, 19),
    strongest_onshore_wind_kmh=70.0,
)


def _service(
    publisher: FakeReportPublisher | FailingReportPublisher, *, days_to_report: int = 2
) -> DailyReportService:
    return DailyReportService(
        tide_source=FakeTideSource(TideForecast(extremes=()), TideForecast(extremes=())),
        weather_source=FakeWeatherSource(_TODAY_WEATHER, _TOMORROW_WEATHER, _OUTLOOK),
        publisher=publisher,
        formatter=ReportFormatter(),
        amber_advisor=AmberAdvisor(),
        timezone="UTC",
        days_to_report=days_to_report,
    )


def test_run_publishes_the_formatted_report() -> None:
    publisher = FakeReportPublisher()
    _service(publisher).run()

    assert len(publisher.published) == 1
    assert "Sunny" in publisher.published[0]


def test_run_publishes_an_html_document() -> None:
    publisher = FakeReportPublisher()
    _service(publisher).run()

    html = publisher.published[0]
    assert html.startswith("<!doctype html>")
    assert "</html>" in html


def test_run_includes_both_days() -> None:
    publisher = FakeReportPublisher()
    _service(publisher).run()

    html = publisher.published[0]
    assert "Today" in html
    assert "Tomorrow" in html
    assert "Sunny" in html
    assert "Cloudy" in html


def test_run_with_days_to_report_one_omits_tomorrow() -> None:
    publisher = FakeReportPublisher()
    _service(publisher, days_to_report=1).run()

    html = publisher.published[0]
    assert "Today" in html
    assert "Tomorrow" not in html
    assert "Sunny" in html
    assert "Cloudy" not in html


def test_run_includes_amber_note_from_advisor() -> None:
    publisher = FakeReportPublisher()
    _service(publisher).run()

    assert "Amber hunting" in publisher.published[0]


def test_run_includes_storm_outlook_once() -> None:
    publisher = FakeReportPublisher()
    _service(publisher).run()

    assert publisher.published[0].count("Wed 19 Aug") == 1


def test_run_propagates_publisher_failures() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        _service(FailingReportPublisher()).run()


def test_label_for_offset_zero_is_today() -> None:
    assert _label_for(0, date(2026, 8, 16)) == "Today"


def test_label_for_offset_one_is_tomorrow() -> None:
    assert _label_for(1, date(2026, 8, 17)) == "Tomorrow"


def test_label_for_offset_beyond_tomorrow_is_the_weekday_name() -> None:
    assert _label_for(2, date(2026, 8, 18)) == "Tuesday"
