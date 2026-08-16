from __future__ import annotations

import logging
import sys

from romo_bot.amber import AmberAdvisor
from romo_bot.clients.dmi_tide import DmiTideTableClient
from romo_bot.clients.file_publisher import FileReportPublisher
from romo_bot.clients.open_meteo import OpenMeteoWeatherClient
from romo_bot.config import ConfigError, Settings
from romo_bot.report import ReportFormatter
from romo_bot.service import DailyReportService


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    try:
        settings = Settings.from_env()
    except ConfigError:
        logging.exception("Configuration error")
        return 1

    service = DailyReportService(
        tide_source=DmiTideTableClient(timezone=settings.timezone),
        weather_source=OpenMeteoWeatherClient(
            settings.latitude, settings.longitude, settings.timezone
        ),
        publisher=FileReportPublisher(settings.output_path),
        formatter=ReportFormatter(),
        amber_advisor=AmberAdvisor(),
        timezone=settings.timezone,
        days_to_report=settings.days_to_report,
    )

    try:
        service.run()
    except Exception:
        logging.exception("Failed to build daily report")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
