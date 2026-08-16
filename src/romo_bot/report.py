from __future__ import annotations

from romo_bot.models import DailyReport, TideDirection

_ARROW = {TideDirection.HIGH: "⬆️ High", TideDirection.LOW: "⬇️ Low"}


class ReportFormatter:
    """Turns a DailyReport into the WhatsApp message text. Formatting only —
    no I/O, no knowledge of where the data came from or where it's going.
    """

    def format(self, report: DailyReport) -> str:
        lines = [
            f"\U0001f30a *Rømø tide & weather — {report.report_date:%A %d %B}*",
            "",
            "*Tides:*",
            *self._format_tide_lines(report),
            "",
            "*Weather:*",
            f"{report.weather.summary}, "
            f"{report.weather.temperature_min_c:.0f}-{report.weather.temperature_max_c:.0f}°C",
            f"\U0001f4a8 Wind up to {report.weather.wind_speed_max_kmh:.0f} km/h",
            "",
            "_Sent automatically · data: open-meteo.com_",
        ]
        return "\n".join(lines)

    @staticmethod
    def _format_tide_lines(report: DailyReport) -> list[str]:
        if not report.tide.extremes:
            return ["Tide data unavailable today."]
        return [
            f"{_ARROW[extreme.direction]} tide ~{extreme.at:%H:%M} ({extreme.height_m:.2f} m)"
            for extreme in report.tide.extremes
        ]
