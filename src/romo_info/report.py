from __future__ import annotations

from html import escape

from romo_info.models import DailyReport, DayForecast, TideDirection, TideForecast, WeatherForecast

_ARROW = {TideDirection.HIGH: "⬆️ High", TideDirection.LOW: "⬇️ Low"}
_DAY_PART_EMOJI = {"Morning": "\U0001f305", "Afternoon": "☀️", "Evening": "\U0001f306"}
# Below this, the chance of rain isn't worth the extra words on the page.
_RAIN_MENTION_THRESHOLD_PCT = 20

_CSS = """
:root { color-scheme: light dark; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  max-width: 640px;
  margin: 0 auto;
  padding: 1.5rem;
  line-height: 1.5;
}
h1 { font-size: 1.5rem; margin-bottom: 0.25rem; }
.updated { color: #767676; margin-top: 0; font-size: 0.9rem; }
.day { border: 1px solid #80808040; border-radius: 12px; padding: 1rem 1.25rem; margin: 1rem 0; }
.day h2 { margin-top: 0; font-size: 1.15rem; }
.day h3 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #767676;
  margin-bottom: 0.4rem;
}
.day ul { margin: 0 0 0.75rem; padding-left: 1.1rem; }
.wind { color: #767676; font-size: 0.9rem; }
.amber { margin-top: 0.75rem; }
.outlook { margin-top: 1.5rem; }
footer { margin-top: 2rem; color: #767676; font-size: 0.85rem; }
"""


class ReportFormatter:
    """Renders a DailyReport as a self-contained static HTML page.

    Formatting only -- no I/O, no knowledge of where the data came from or
    where the page ends up published.
    """

    def format(self, report: DailyReport) -> str:
        days_html = "\n".join(self._format_day(day) for day in report.days)
        updated = escape(f"{report.report_date:%A %d %B, %H:%M}")
        outlook = escape(report.storm_outlook_note)
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rømø tide &amp; weather</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<h1>\U0001f30a Rømø tide &amp; weather</h1>
<p class="updated">Updated {updated}</p>
{days_html}
<section class="outlook">
<h2>Amber storm outlook</h2>
<p>{outlook}</p>
</section>
<footer>Generated automatically &middot; data: DMI, open-meteo.com</footer>
</main>
</body>
</html>
"""

    def _format_day(self, day: DayForecast) -> str:
        return (
            f'<section class="day">\n'
            f"<h2>{escape(day.label)} ({day.for_date:%a %d %b})</h2>\n"
            f"<h3>Tides</h3>\n"
            f"<ul>{self._format_tide_lines(day.tide)}</ul>\n"
            f"<h3>Weather</h3>\n"
            f"<ul>{self._format_weather_lines(day.weather)}</ul>\n"
            f'<p class="wind">\U0001f4a8 Wind up to {day.weather.wind_speed_max_kmh:.0f} km/h</p>\n'
            f"<h3>Amber hunting</h3>\n"
            f'<p class="amber">{escape(day.amber_note)}</p>\n'
            f"</section>"
        )

    @staticmethod
    def _format_tide_lines(tide: TideForecast) -> str:
        if not tide.extremes:
            return "<li>Tide data unavailable.</li>"
        return "".join(
            f"<li>{_ARROW[extreme.direction]} tide ~{extreme.at:%H:%M} "
            f"({extreme.height_m:.2f} m)</li>"
            for extreme in tide.extremes
        )

    @staticmethod
    def _format_weather_lines(weather: WeatherForecast) -> str:
        if not weather.day_parts:
            return "<li>Weather data unavailable.</li>"
        return "".join(
            f"<li>{_DAY_PART_EMOJI.get(part.label, '')} {escape(part.label)}: "
            f"{escape(part.summary)}, {part.temperature_c:.0f}°C"
            f"{ReportFormatter._rain_chance(part.precipitation_probability_pct)}</li>"
            for part in weather.day_parts
        )

    @staticmethod
    def _rain_chance(probability_pct: int) -> str:
        """Mention the chance of rain only when it's worth acting on.

        Printing "0% rain" on every dry window is noise, and a token few
        percent isn't decision-changing either.
        """
        if probability_pct < _RAIN_MENTION_THRESHOLD_PCT:
            return ""
        return f" \U0001f327️ {probability_pct}%"
