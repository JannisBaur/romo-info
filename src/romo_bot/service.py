from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from romo_bot.amber import AmberAdvisor
from romo_bot.clients.protocols import ReportPublisher, TideDataSource, WeatherDataSource
from romo_bot.models import DailyReport, DayForecast
from romo_bot.report import ReportFormatter

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
    amber_advisor: AmberAdvisor
    timezone: str
    days_to_report: int

    def run(self) -> None:
        tides = self.tide_source.fetch_tide_forecast(self.days_to_report)
        weathers, storm_outlook = self.weather_source.fetch_weather_forecast(self.days_to_report)
        now = datetime.now(ZoneInfo(self.timezone))

        days = tuple(
            DayForecast(
                for_date=now.date() + timedelta(days=offset),
                label=_label_for(offset, now.date() + timedelta(days=offset)),
                tide=tides[offset],
                weather=weathers[offset],
                amber_note=self.amber_advisor.suggest(weathers[offset], tides[offset]),
            )
            for offset in range(self.days_to_report)
        )

        report = DailyReport(
            report_date=now,
            days=days,
            storm_outlook_note=self.amber_advisor.describe_outlook(storm_outlook),
        )
        html = self.formatter.format(report)
        self.publisher.publish(html)
        logger.info("Report published.")
