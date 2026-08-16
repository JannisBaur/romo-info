from __future__ import annotations

from datetime import datetime

from romo_bot.models import (
    DailyReport,
    DayPartForecast,
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
            day_parts=(
                DayPartForecast(label="Morning", summary="Partly cloudy", temperature_c=14.0),
                DayPartForecast(label="Afternoon", summary="Clear sky", temperature_c=19.0),
                DayPartForecast(label="Evening", summary="Overcast", temperature_c=16.0),
            ),
            temperature_min_c=14.0,
            temperature_max_c=19.0,
            wind_speed_max_kmh=22.0,
            wind_direction_deg=270.0,
            recent_onshore_storm=True,
        ),
        amber_note=(
            "Good conditions — strong onshore wind (22 km/h). Best around low tide (~09:00)."
        ),
    )


def test_tide_extremes_appear_in_chronological_order() -> None:
    text = ReportFormatter().format(_report())
    assert text.index("High tide") < text.index("Low tide")
    assert "03:00" in text
    assert "09:00" in text


def test_weather_day_parts_are_included_in_order() -> None:
    text = ReportFormatter().format(_report())
    assert text.index("Morning") < text.index("Afternoon") < text.index("Evening")
    assert "Partly cloudy" in text
    assert "Clear sky" in text
    assert "Overcast" in text
    assert "14" in text
    assert "19" in text


def test_wind_speed_is_included() -> None:
    text = ReportFormatter().format(_report())
    assert "22" in text


def test_amber_note_is_included() -> None:
    text = ReportFormatter().format(_report())
    assert "Amber hunting" in text
    assert "strong onshore wind" in text


def test_missing_tide_data_shows_fallback_message() -> None:
    report = _report()
    empty_tide = DailyReport(
        report_date=report.report_date,
        tide=TideForecast(extremes=()),
        weather=report.weather,
        amber_note=report.amber_note,
    )
    text = ReportFormatter().format(empty_tide)
    assert "unavailable" in text.lower()


def test_missing_weather_data_shows_fallback_message() -> None:
    report = _report()
    empty_weather = DailyReport(
        report_date=report.report_date,
        tide=report.tide,
        weather=WeatherForecast(
            day_parts=(),
            temperature_min_c=0.0,
            temperature_max_c=0.0,
            wind_speed_max_kmh=0.0,
            wind_direction_deg=0.0,
            recent_onshore_storm=False,
        ),
        amber_note=report.amber_note,
    )
    text = ReportFormatter().format(empty_weather)
    assert "unavailable" in text.lower()
