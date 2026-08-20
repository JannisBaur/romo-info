from __future__ import annotations

from datetime import date, datetime

from romo_info.models import (
    DailyReport,
    DayForecast,
    TideDirection,
    TideExtreme,
    TideForecast,
    WeatherForecast,
)
from romo_info.report import ReportFormatter


def _weather(*, storm: bool = True) -> WeatherForecast:
    return WeatherForecast(
        wind_speed_max_kmh=22.0,
        wind_direction_deg=250.0,
        recent_onshore_storm=storm,
        recent_storm_lookback_days=3,
        recent_strongest_onshore_kmh=None,
        recent_strongest_onshore_date=None,
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
        stargazing_note="\U0001f30c Dark 22:00\u201305:00 · 10% cloud.",
        meteor_note="\U0001f320 Perseids peaked Thu 13 Aug, tailing off.",
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


def test_wind_speed_is_included() -> None:
    html = ReportFormatter().format(_report())
    assert "22" in html
    assert "km/h" in html


def test_general_conditions_are_not_reported() -> None:
    # Temperature, cloud and chance of rain were dropped deliberately --
    # any weather app does them better, and summarising a six-hour window
    # in one number kept being misleading.
    html = ReportFormatter().format(_report())
    assert "°C" not in html
    assert "Morning" not in html
    assert "Afternoon" not in html


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
            stargazing_note="\U0001f30c Dark 22:00\u201305:00 · 10% cloud.",
            meteor_note="\U0001f320 Perseids peaked Thu 13 Aug, tailing off.",
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
            stargazing_note="\U0001f30c Dark 22:00\u201305:00 · 10% cloud.",
            meteor_note="\U0001f320 Perseids peaked Thu 13 Aug, tailing off.",
        )
    )
    assert "unavailable" in html.lower()


def test_page_references_the_mascot_image() -> None:
    html = ReportFormatter().format(_report())
    # Relative src -- FileReportPublisher copies the file into the same
    # directory as index.html.
    assert 'src="dog.jpg"' in html
    # Empty alt marks it decorative, so screen readers skip it silently
    # rather than falling back to announcing the filename.
    assert 'alt=""' in html


def test_wind_direction_and_shore_are_reported() -> None:
    # The bearing alone doesn't tell you what matters for amber, so the
    # page states onshore/offshore outright.
    html = ReportFormatter().format(_report())
    assert "WSW" in html
    assert "250°" in html
    assert "onshore" in html


def test_days_and_outlook_share_the_card_styling() -> None:
    # They are peers on the page. Without the shared class the outlook's
    # h2 falls back to the browser default and dwarfs the day headings.
    html = ReportFormatter().format(_report())
    assert '<section class="card day">' in html
    assert '<section class="card outlook">' in html


def test_where_to_look_section_is_present_with_sources() -> None:
    # Static local knowledge, but it makes claims, so it has to cite them.
    html = ReportFormatter().format(_report())
    assert "Where to find amber" in html
    assert "Lakolk" in html
    assert "ravpindelag" in html
    assert "Sources:" in html
    assert "ravvejr.dk" in html


def test_page_carries_a_safety_and_affiliation_disclaimer() -> None:
    # The Wadden Sea flats flood fast, so the page must not read as
    # something to plan a walk out on.
    html = ReportFormatter().format(_report())
    assert "not a safety" in html
    assert "not affiliated" in html


def test_page_credits_ravvejr_rather_than_restating_their_forecast() -> None:
    # Their scored amber probability is their product -- link to it, don't
    # republish it.
    html = ReportFormatter().format(_report())
    assert "ravvejr.dk/lakolk-strand/" in html


def test_amber_sections_are_grouped_before_the_sky_section() -> None:
    # "Where to find amber" sitting after Stargazing read as sky advice and
    # split the amber content in two.
    html = ReportFormatter().format(_report())
    assert html.index("Amber storm outlook") < html.index("Where to find amber")
    assert html.index("Where to find amber") < html.index("Stargazing tonight")
