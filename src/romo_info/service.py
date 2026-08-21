from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from romo_info.clients.protocols import ReportPublisher, TideDataSource, WeatherDataSource
from romo_info.meteors import describe as describe_meteors
from romo_info.models import DailyReport, DayForecast
from romo_info.report import ReportFormatter
from romo_info.stargazing import describe as describe_stargazing
from romo_info.tide import falling_tide_note

logger = logging.getLogger(__name__)


def _label_for(offset: int, for_date: date) -> str:
    """Today/Tomorrow for the first two days, then the weekday name -- pure
    so it's trivially testable without a full report round-trip.
    """
    if offset == 0:
        return "Today"
    if offset == 1:
        return "Tomorrow"
    return for_date.strftime("%A")


@dataclass(frozen=True, slots=True)
class DailyReportService:
    """Orchestrates fetching data, formatting it, and publishing the report.

    Depends only on narrow protocols (dependency inversion), so each piece
    -- data source, publisher -- can be swapped or faked independently in
    tests without touching this class.
    """

    tide_source: TideDataSource
    weather_source: WeatherDataSource
    publisher: ReportPublisher
    formatter: ReportFormatter
    timezone: str
    days_to_report: int
    # Only used to decide whether a shower's radiant rises here.
    latitude: float

    def run(self) -> None:
        tides = self.tide_source.fetch_tide_forecast(self.days_to_report)
        weathers, stargazing = self.weather_source.fetch_weather_forecast(self.days_to_report)
        now = datetime.now(ZoneInfo(self.timezone))

        days = tuple(
            DayForecast(
                for_date=now.date() + timedelta(days=offset),
                label=_label_for(offset, now.date() + timedelta(days=offset)),
                tide=tides[offset],
                weather=weathers[offset],
                tide_note=falling_tide_note(tides[offset]),
            )
            for offset in range(self.days_to_report)
        )

        report = DailyReport(
            report_date=now,
            days=days,
            stargazing_note=describe_stargazing(stargazing),
            meteor_note=describe_meteors(now.date(), self.latitude),
        )
        html = self.formatter.format(report)
        self.publisher.publish(html)
        logger.info("Report published.")
