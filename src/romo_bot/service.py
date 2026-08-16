from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from romo_bot.amber import AmberAdvisor
from romo_bot.clients.protocols import MessageSender, TideDataSource, WeatherDataSource
from romo_bot.models import DailyReport, DayForecast
from romo_bot.report import ReportFormatter

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DailyReportService:
    """Orchestrates fetching data, formatting it, and delivering the report.

    Depends only on narrow protocols (dependency inversion), so each piece
    -- data source, sender -- can be swapped or faked independently in tests
    without touching this class.
    """

    tide_source: TideDataSource
    weather_source: WeatherDataSource
    sender: MessageSender
    formatter: ReportFormatter
    amber_advisor: AmberAdvisor
    group_jid: str
    timezone: str

    def run(self) -> None:
        today_tide, tomorrow_tide = self.tide_source.fetch_tide_forecast()
        today_weather, tomorrow_weather = self.weather_source.fetch_weather_forecast()
        now = datetime.now(ZoneInfo(self.timezone))

        report = DailyReport(
            report_date=now,
            days=(
                DayForecast(
                    for_date=now.date(),
                    label="Today",
                    tide=today_tide,
                    weather=today_weather,
                    amber_note=self.amber_advisor.suggest(today_weather, today_tide),
                ),
                DayForecast(
                    for_date=now.date() + timedelta(days=1),
                    label="Tomorrow",
                    tide=tomorrow_tide,
                    weather=tomorrow_weather,
                    amber_note=self.amber_advisor.suggest(tomorrow_weather, tomorrow_tide),
                ),
            ),
        )
        message = self.formatter.format(report)
        logger.info("Sending daily report to %s", self.group_jid)
        self.sender.send(self.group_jid, message)
        logger.info("Report sent.")
