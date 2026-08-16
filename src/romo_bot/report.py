from __future__ import annotations

from romo_bot.models import DailyReport, DayForecast, TideDirection, TideForecast, WeatherForecast

_ARROW = {TideDirection.HIGH: "⬆️ High", TideDirection.LOW: "⬇️ Low"}
_DAY_PART_EMOJI = {"Morning": "\U0001f305", "Afternoon": "☀️", "Evening": "\U0001f306"}


class ReportFormatter:
    """Turns a DailyReport into the WhatsApp message text. Formatting only —
    no I/O, no knowledge of where the data came from or where it's going.
    """

    def format(self, report: DailyReport) -> str:
        lines = [f"\U0001f30a *Rømø tide & weather — {report.report_date:%A %d %B}*", ""]
        for day in report.days:
            lines.extend(self._format_day(day))
            lines.append("")
        lines.append("_Sent automatically · data: DMI, open-meteo.com_")
        return "\n".join(lines)

    def _format_day(self, day: DayForecast) -> list[str]:
        return [
            f"*{day.label} ({day.for_date:%a %d %b})*",
            "",
            "*Tides:*",
            *self._format_tide_lines(day.tide),
            "",
            "*Weather:*",
            *self._format_weather_lines(day.weather),
            f"\U0001f4a8 Wind up to {day.weather.wind_speed_max_kmh:.0f} km/h",
            "",
            "*Amber hunting:*",
            day.amber_note,
        ]

    @staticmethod
    def _format_tide_lines(tide: TideForecast) -> list[str]:
        if not tide.extremes:
            return ["Tide data unavailable."]
        return [
            f"{_ARROW[extreme.direction]} tide ~{extreme.at:%H:%M} ({extreme.height_m:.2f} m)"
            for extreme in tide.extremes
        ]

    @staticmethod
    def _format_weather_lines(weather: WeatherForecast) -> list[str]:
        if not weather.day_parts:
            return ["Weather data unavailable."]
        return [
            f"{_DAY_PART_EMOJI.get(part.label, '')} {part.label}: {part.summary}, "
            f"{part.temperature_c:.0f}°C"
            for part in weather.day_parts
        ]
