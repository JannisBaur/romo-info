from __future__ import annotations

from datetime import date, datetime

from romo_info.models import (
    DailyReport,
    DayForecast,
    DayPartForecast,
    TideDirection,
    TideExtreme,
    TideForecast,
    WeatherForecast,
)
from romo_info.report import ReportFormatter


def _weather(*, storm: bool = True) -> WeatherForecast:
    return WeatherForecast(
        day_parts=(
            DayPartForecast(
                label="Morning",
                summary="Partly cloudy",
                temperature_c=14.0,
                precipitation_probability_pct=0,
            ),
            DayPartForecast(
                label="Afternoon",
                summary="Clear sky",
                temperature_c=19.0,
                precipitation_probability_pct=0,
            ),
            DayPartForecast(
                label="Evening",
                summary="Overcast",
                temperature_c=16.0,
                precipitation_probability_pct=0,
            ),
        ),
        temperature_min_c=14.0,
        temperature_max_c=19.0,
        wind_speed_max_kmh=22.0,
        wind_direction_deg=270.0,
        recent_onshore_storm=storm,
        recent_storm_lookback_days=3,
        recent_strongest_onshore_kmh=None,
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
        storm_outlook_note="\U0001f52e No storm forecast through Sat 22 Aug.",
    )


def test_output_is_a_complete_html_document() -> None:
    html = ReportFormatter().format(_report())
    assert html.startswith("<!doctype html>")
    assert '<meta name="viewport"' in html
    assert html.rstrip().endswith("</html>")


def test_tide_extremes_appear_in_chronological_order() -> None:
    html = ReportFormatter().format(_report())
    assert html.index("High tide") < html.index("Low tide")
    assert "03:00" in html
    assert "09:00" in html


def test_both_days_are_included_in_order() -> None:
    html = ReportFormatter().format(_report())
    assert html.index("Today") < html.index("Tomorrow")


def test_weather_day_parts_are_included_in_order() -> None:
    html = ReportFormatter().format(_report())
    assert html.index("Morning") < html.index("Afternoon") < html.index("Evening")
    assert "Partly cloudy" in html
    assert "Clear sky" in html
    assert "Overcast" in html
    assert "14" in html
    assert "19" in html


def test_wind_speed_is_included() -> None:
    html = ReportFormatter().format(_report())
    assert "22" in html


def test_amber_notes_for_both_days_are_included() -> None:
    html = ReportFormatter().format(_report())
    assert "Amber hunting" in html
    assert "strong onshore wind" in html
    assert "No recent storm" in html


def test_storm_outlook_appears_once_not_per_day() -> None:
    html = ReportFormatter().format(_report())
    assert html.count("No storm forecast through Sat 22 Aug") == 1
    assert "Amber storm outlook" in html


def test_text_from_the_report_is_html_escaped() -> None:
    # Nothing in the pipeline produces markup today, but the formatter must
    # not become an injection point if a data source ever returns "<" or "&".
    report = _report()
    today = report.days[0]
    html = ReportFormatter().format(
        DailyReport(
            report_date=report.report_date,
            days=(
                DayForecast(
                    for_date=today.for_date,
                    label=today.label,
                    tide=today.tide,
                    weather=today.weather,
                    amber_note="<script>alert('x')</script> & more",
                ),
            ),
            storm_outlook_note=report.storm_outlook_note,
        )
    )
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "&amp; more" in html


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
    html = ReportFormatter().format(
        DailyReport(
            report_date=report.report_date,
            days=(empty_tide_today, report.days[1]),
            storm_outlook_note=report.storm_outlook_note,
        )
    )
    assert "unavailable" in html.lower()


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
            recent_storm_lookback_days=3,
            recent_strongest_onshore_kmh=None,
        ),
        amber_note=today.amber_note,
    )
    html = ReportFormatter().format(
        DailyReport(
            report_date=report.report_date,
            days=(empty_weather_today, report.days[1]),
            storm_outlook_note=report.storm_outlook_note,
        )
    )
    assert "unavailable" in html.lower()


def test_meaningful_rain_chance_is_shown() -> None:
    report = _report()
    today = report.days[0]
    html = ReportFormatter().format(
        DailyReport(
            report_date=report.report_date,
            days=(
                DayForecast(
                    for_date=today.for_date,
                    label=today.label,
                    tide=today.tide,
                    weather=WeatherForecast(
                        day_parts=(
                            DayPartForecast(
                                label="Morning",
                                summary="Partly cloudy",
                                temperature_c=14.0,
                                precipitation_probability_pct=40,
                            ),
                        ),
                        temperature_min_c=14.0,
                        temperature_max_c=19.0,
                        wind_speed_max_kmh=22.0,
                        wind_direction_deg=270.0,
                        recent_onshore_storm=False,
                        recent_storm_lookback_days=3,
                        recent_strongest_onshore_kmh=None,
                    ),
                    amber_note=today.amber_note,
                ),
            ),
            storm_outlook_note=report.storm_outlook_note,
        )
    )
    assert "40%" in html


def test_negligible_rain_chance_is_omitted_as_noise() -> None:
    # Printing "0% rain" on every dry window would be pure clutter. Assert
    # on the rain marker itself rather than a bare "0%", which also matches
    # CSS such as "max-width: 60%".
    html = ReportFormatter().format(_report())
    assert "\U0001f327" not in html


def test_page_references_the_mascot_image() -> None:
    html = ReportFormatter().format(_report())
    # Relative src -- FileReportPublisher copies the file into the same
    # directory as index.html.
    assert 'src="dog.jpg"' in html
    assert "alt=" in html
