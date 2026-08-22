from __future__ import annotations

from dataclasses import dataclass
from html import escape

from romo_info.models import (
    DailyReport,
    DayForecast,
    TideDirection,
    TideForecast,
    WeatherForecast,
)
from romo_info.weather import compass_point, is_onshore

# These two earn their place: they distinguish high from low at a
# glance, where the rest of the page's emoji were decoration applied
# unevenly. Emoji otherwise appear only on section headings and the
# jump links that restate them.
_ARROW = {TideDirection.HIGH: "⬆️ High", TideDirection.LOW: "⬇️ Low"}


@dataclass(frozen=True, slots=True)
class _Section:
    """One of the page's top-level sections.

    Heading and jump link are rendered from the same entry so a link can
    never point at a heading that has been renamed out from under it.
    """

    anchor: str
    # Pre-escaped: these are fixed strings, not data from an API.
    title: str

    def heading(self) -> str:
        return f'<h2 class="group" id="{self.anchor}">{self.title}</h2>'

    def link(self) -> str:
        return f'<a href="#{self.anchor}">{self.title}</a>'


_SECTIONS = (
    _Section("tides", "\U0001f30a Tides &amp; wind"),
    _Section("amber", "\U0001f50e Amber"),
    _Section("stargazing", "\U0001f30c Stargazing"),
)
_TIDES, _AMBER, _STARGAZING = _SECTIONS

# Jump links. The page is one long scroll on a phone -- three days of
# tides push stargazing well below the fold -- and the ids double as
# shareable deep links (.../#stargazing).
_NAV = '<nav class="jump">' + "".join(section.link() for section in _SECTIONS) + "</nav>"

# Fixed local knowledge -- it doesn't change day to day, so it's baked in
# rather than fetched. Sourced rather than folklore: see the links below.
_WHERE_TO_LOOK = """<section class="card tips">
<p class="lead">For odds, check
<a href="https://ravvejr.dk/lakolk-strand/">Ravvejr's 5-day amber forecast for Lakolk</a>.
Below is just where and how to look once you're there.</p>
<ul>
<li><strong>Lakolk</strong>, or the northern end of Sønderstrand — that stretch faces
due west, so it takes the west and north-westerly storms most squarely. Sønderstrand's
southern tip swings round towards the south and catches them more obliquely.</li>
<li>Walk the <strong>wrack lines</strong>, not open sand. Amber is only slightly denser
than seawater, so it strands alongside everything else of similar density rather than
sinking where it lands.</li>
<li>That line is the giveaway: seaweed, twigs, <strong>dark waterlogged wood and
coal</strong>, shells. Danish hunters call it the <em>ravpindelag</em> — the
amber-stick layer. Find that band and you're searching the right stripe of beach.</li>
<li>Diving gulls mark the same debris, for the same reason.</li>
<li>Best on the <strong>second falling tide after a storm</strong>, and better in winter
— the storms are bigger, and amber floats more readily in cold, denser water.</li>
</ul>
<p class="sources">Sources:
<a href="https://ravvejr.dk/guide-til-at-finde-rav/">Ravvejr</a>,
<a href="https://samvirke.dk/artikler/saadan-finder-du-rav">Samvirke</a>,
<a href="https://danskenaturparker.dk/aktiviteter/saadan-finder-du-rav">Danske Naturparker</a>,
<a href="https://ravvejr.dk/lakolk-strand/">Ravvejr on Lakolk</a></p>
</section>"""

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
/* Every section is a peer, so they share one card style -- otherwise a
   section's h2 falls back to the browser default and reads as a
   page-level heading rather than another section. */
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
/* The page's three sections. They sit above the cards rather than
   inside them so all three are named the same way -- previously the
   days got a faded outside label while amber and stargazing carried
   bold titles within their cards, which made peers look unrelated.
   Sized between the page title and a card heading, so the hierarchy
   reads h1 > section > card. */
.group { font-size: 1.25rem; margin: 2rem 0 0.5rem; }
/* Without this an anchor jump leaves the heading flush against the top
   edge of the viewport, reading as if it were cut off. */
.group[id] { scroll-margin-top: 1rem; }
.jump { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.75rem 0 0; }
.jump a {
  border: 1px solid #80808040;
  border-radius: 999px;
  padding: 0.2rem 0.7rem;
  font-size: 0.85rem;
  text-decoration: none;
}
.wind { color: #767676; font-size: 0.9rem; }
.lead { margin-top: 0; }
.tips ul { margin: 0; padding-left: 1.1rem; }
.tips li { margin-bottom: 0.5rem; }
.sources { font-size: 0.8rem; color: #767676; margin-top: 0.9rem; }
/* Five lines of small print hanging under a centred credit line read as
   a mistake rather than a choice. Centring them instead would give five
   ragged edges, which is worse -- so it keeps its left edge and is set
   apart deliberately, with a rule above it. Its left edge sits at the
   body edge, the same line the section headings and card borders use,
   so it lines up with the page instead of floating free. */
.disclaimer {
  text-align: left;
  font-size: 0.8rem;
  line-height: 1.45;
  margin: 1.25rem 0 0;
  padding: 0.9rem 0 0;
  border-top: 1px solid #80808040;
  /* Justified so the block has two straight edges instead of a ragged
     right one -- the usual setting for a block of fine print. Hyphens
     are what make that work at this width: without them, justifying a
     narrow phone column stretches word spacing into visible gaps.
     Needs the lang attribute on <html>, which is set. */
  text-align: justify;
  hyphens: auto;
}
.requested { font-size: 0.8rem; color: #767676; margin-top: 0.6rem; }
.meteors { margin-top: 0.6rem; }
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
        stargazing = escape(report.stargazing_note)
        # Rendered only when a shower is actually running.
        meteors = (
            f'<p class="meteors">{escape(report.meteor_note)}</p>\n' if report.meteor_note else ""
        )
        return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Rømø info</title>
<style>{_CSS}</style>
</head>
<body>
<main>
<h1>\U0001f3dd\ufe0f Rømø info</h1>
<p class="updated">Updated {updated}</p>
{_NAV}
{_TIDES.heading()}
{days_html}
{_AMBER.heading()}
{_WHERE_TO_LOOK}
{_STARGAZING.heading()}
<section class="card stars">
<p>{stargazing}</p>
{meteors}<p class="requested">Requested by Pia</p>
</section>
<footer>
<img class="mascot" src="dog.jpg" width="100" height="100" alt="">
<p>Generated automatically &middot; data: DMI, open-meteo.com</p>
<p class="disclaimer">Personal hobby page, not affiliated with DMI, Open-Meteo or
Ravvejr. Tide and wind figures are model predictions and this is <strong>not a safety
tool</strong> — the Wadden Sea flats flood quickly and cut off routes back, so check
official tide tables and local warnings before walking out.</p>
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
            f"</section>"
        )

    @staticmethod
    def _format_wind(weather: WeatherForecast) -> str:
        # Onshore vs offshore is the part that matters for amber, so say it
        # outright rather than leaving the reader to decode the bearing.
        shore = "onshore" if is_onshore(weather.wind_direction_deg) else "offshore"
        return (
            f"Up to {weather.wind_speed_max_kmh:.0f} km/h from "
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
