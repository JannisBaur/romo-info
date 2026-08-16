from __future__ import annotations

from datetime import datetime

from romo_bot.models import (
    DailyReport,
    TideDirection,
    TideExtreme,
    TideForecast,
    WeatherForecast,
)
from romo_bot.report import ReportFormatter


def _report() -> DailyReport:
    return DailyReport(
        report_date=datetime(2026, 8, 16, 7, 0),
        tide=TideForecast(
            extremes=(
                TideExtreme(datetime(2026, 8, 16, 3, 0), 1.8, TideDirection.HIGH),
                TideExtreme(datetime(2026, 8, 16, 9, 0), 0.2, TideDirection.LOW),
            )
        ),
        weather=WeatherForecast(
            summary="Partly cloudy",
            temperature_min_c=14.0,
            temperature_max_c=19.0,
            wind_speed_max_kmh=22.0,
        ),
    )


def test_tide_extremes_appear_in_chronological_order() -> None:
    text = ReportFormatter().format(_report())
    assert text.index("High tide") < text.index("Low tide")
    assert "03:00" in text
    assert "09:00" in text


def test_weather_summary_is_included() -> None:
    text = ReportFormatter().format(_report())
    assert "Partly cloudy" in text
    assert "14" in text
    assert "19" in text
    assert "22" in text


def test_missing_tide_data_shows_fallback_message() -> None:
    report = _report()
    empty_tide = DailyReport(
        report_date=report.report_date,
        tide=TideForecast(extremes=()),
        weather=report.weather,
    )
    text = ReportFormatter().format(empty_tide)
    assert "unavailable" in text.lower()
