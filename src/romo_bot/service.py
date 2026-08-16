from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from romo_bot.amber import AmberAdvisor
from romo_bot.clients.protocols import MessageSender, TideDataSource, WeatherDataSource
from romo_bot.models import DailyReport
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
        tide = self.tide_source.fetch_tide_forecast()
        weather = self.weather_source.fetch_weather_forecast()
        report = DailyReport(
            report_date=datetime.now(ZoneInfo(self.timezone)),
            tide=tide,
            weather=weather,
            amber_note=self.amber_advisor.suggest(weather, tide),
        )
        message = self.formatter.format(report)
        logger.info("Sending daily report to %s", self.group_jid)
        self.sender.send(self.group_jid, message)
        logger.info("Report sent.")
