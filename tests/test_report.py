from __future__ import annotations

from datetime import date, datetime

from romo_bot.models import (
    DailyReport,
    DayForecast,
    DayPartForecast,
    TideDirection,
    TideExtreme,
    TideForecast,
    WeatherForecast,
)
from romo_bot.report import ReportFormatter


def _weather(*, storm: bool = True) -> WeatherForecast:
    return WeatherForecast(
        day_parts=(
            DayPartForecast(label="Morning", summary="Partly cloudy", temperature_c=14.0),
            DayPartForecast(label="Afternoon", summary="Clear sky", temperature_c=19.0),
            DayPartForecast(label="Evening", summary="Overcast", temperature_c=16.0),
        ),
        temperature_min_c=14.0,
        temperature_max_c=19.0,
        wind_speed_max_kmh=22.0,
        wind_direction_deg=270.0,
        recent_onshore_storm=storm,
    )


def _tide() -> TideForecast:
    return TideForecast(
        extremes=(
            TideExtreme(datetime(2026, 8, 16, 3, 0), 1.8, TideDirection.HIGH),
            TideExtreme(datetime(2026, 8, 16, 9, 0), 0.2, TideDirection.LOW),
        )
    )


def _report() -> DailyReport:
    return DailyReport(
        report_date=datetime(2026, 8, 16, 7, 0),
        days=(
            DayForecast(
                for_date=date(2026, 8, 16),
                label="Today",
                tide=_tide(),
                weather=_weather(),
                amber_note=(
                    "Good conditions — strong onshore wind. Best around low tide (~09:00)."
                ),
            ),
            DayForecast(
                for_date=date(2026, 8, 17),
                label="Tomorrow",
                tide=TideForecast(
                    extremes=(TideExtreme(datetime(2026, 8, 17, 4, 0), 1.9, TideDirection.HIGH),)
                ),
                weather=_weather(storm=False),
                amber_note="No recent storm to loosen amber, less likely tomorrow.",
            ),
        ),
    )


def test_tide_extremes_appear_in_chronological_order() -> None:
    text = ReportFormatter().format(_report())
    assert text.index("High tide") < text.index("Low tide")
    assert "03:00" in text
    assert "09:00" in text


def test_both_days_are_included_in_order() -> None:
    text = ReportFormatter().format(_report())
    assert text.index("Today") < text.index("Tomorrow")


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


def test_amber_notes_for_both_days_are_included() -> None:
    text = ReportFormatter().format(_report())
    assert "Amber hunting" in text
    assert "strong onshore wind" in text
    assert "No recent storm" in text


def test_missing_tide_data_shows_fallback_message() -> None:
    report = _report()
    today = report.days[0]
    empty_tide_today = DayForecast(
        for_date=today.for_date,
        label=today.label,
        tide=TideForecast(extremes=()),
        weather=today.weather,
        amber_note=today.amber_note,
    )
    text = ReportFormatter().format(
        DailyReport(report_date=report.report_date, days=(empty_tide_today, report.days[1]))
    )
    assert "unavailable" in text.lower()


def test_missing_weather_data_shows_fallback_message() -> None:
    report = _report()
    today = report.days[0]
    empty_weather_today = DayForecast(
        for_date=today.for_date,
        label=today.label,
        tide=today.tide,
        weather=WeatherForecast(
            day_parts=(),
            temperature_min_c=0.0,
            temperature_max_c=0.0,
            wind_speed_max_kmh=0.0,
            wind_direction_deg=0.0,
            recent_onshore_storm=False,
        ),
        amber_note=today.amber_note,
    )
    text = ReportFormatter().format(
        DailyReport(report_date=report.report_date, days=(empty_weather_today, report.days[1]))
    )
    assert "unavailable" in text.lower()
