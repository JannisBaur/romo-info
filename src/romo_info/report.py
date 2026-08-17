from __future__ import annotations

from html import escape

from romo_info.models import (
    DailyReport,
    DayForecast,
    TideDirection,
    TideForecast,
    WeatherForecast,
)
from romo_info.weather import compass_point, is_onshore

_ARROW = {TideDirection.HIGH: "⬆️ High", TideDirection.LOW: "⬇️ Low"}

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
.mascot {
  display: block;
  width: 100px;
  height: 100px;
  max-width: 40%;
  object-fit: cover;
  border-radius: 50%;
  margin: 0 auto 0.75rem;
}
/* Days and the storm outlook are peers, so they share one card style --
   otherwise the outlook's h2 falls back to the browser default and reads
   as a page-level heading rather than another section. */
.card { border: 1px solid #80808040; border-radius: 12px; padding: 1rem 1.25rem; margin: 1rem 0; }
.card h2 { margin-top: 0; font-size: 1.15rem; }
.card h3 {
  font-size: 0.85rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: #767676;
  margin-bottom: 0.4rem;
}
.card p:last-child { margin-bottom: 0; }
.card ul { margin: 0 0 0.75rem; padding-left: 1.1rem; }
.wind { color: #767676; font-size: 0.9rem; }
.amber { margin-top: 0.75rem; }
footer { margin-top: 2rem; color: #767676; font-size: 0.85rem; text-align: center; }
footer p { margin: 0; }
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
<title>Rømø tides &amp; amber</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<h1>\U0001f30a Rømø tides &amp; amber</h1>
<p class="updated">Updated {updated}</p>
{days_html}
<section class="card outlook">
<h2>Amber storm outlook</h2>
<p>{outlook}</p>
</section>
<footer>
<img class="mascot" src="dog.jpg" width="100" height="100" alt="">
<p>Generated automatically &middot; data: DMI, open-meteo.com</p>
</footer>
</main>
</body>
</html>
"""

    def _format_day(self, day: DayForecast) -> str:
        return (
            f'<section class="card day">\n'
            f"<h2>{escape(day.label)} ({day.for_date:%a %d %b})</h2>\n"
            f"<h3>Tides</h3>\n"
            f"<ul>{self._format_tide_lines(day.tide)}</ul>\n"
            f"<h3>Wind</h3>\n"
            f'<p class="wind">{self._format_wind(day.weather)}</p>\n'
            f"<h3>Amber hunting</h3>\n"
            f'<p class="amber">{escape(day.amber_note)}</p>\n'
            f"</section>"
        )

    @staticmethod
    def _format_wind(weather: WeatherForecast) -> str:
        # Onshore vs offshore is the part that matters for amber, so say it
        # outright rather than leaving the reader to decode the bearing.
        shore = "onshore" if is_onshore(weather.wind_direction_deg) else "offshore"
        return (
            f"\U0001f4a8 Up to {weather.wind_speed_max_kmh:.0f} km/h from "
            f"{compass_point(weather.wind_direction_deg)} "
            f"({weather.wind_direction_deg:.0f}°) — {shore}"
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
