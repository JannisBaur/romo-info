from __future__ import annotations

from dataclasses import dataclass
from datetime import date

# Every figure below is transcribed from the International Meteor
# Organization's 2026 Meteor Shower Calendar, Table 5 ("Working List of
# Visual Meteor Showers"), IMO INFO(3-25), page 25:
# https://www.imo.net/files/meteor-shower/cal2026.pdf
#
# REFRESH ANNUALLY. The IMO states maximum dates are "accurate only for
# 2026"; activity periods barely move year to year, but peaks shift by a
# day or so, so this table needs replacing when next year's calendar is
# published -- exactly like the bundled tide table.
#
# Not every shower in Table 5 is here. Left out on purpose:
#   * the two daytime showers (Arietids, Sextantids) -- radio-only, you
#     cannot see them at night;
#   * radiants too far south to rise at this latitude (see rises_at);
#   * anything below _WORTH_MENTIONING_ZHR, which would be indistinguishable
#     from the sporadic background;
#   * showers the IMO marks "Var", whose rate it explicitly declines to
#     predict -- inventing a number for those is the one thing this table
#     must not do.
_WORTH_MENTIONING_ZHR = 10


@dataclass(frozen=True, slots=True)
class MeteorShower:
    name: str
    code: str
    # (month, day) -- periods can wrap the new year, see _within_period.
    start: tuple[int, int]
    end: tuple[int, int]
    peak: tuple[int, int]
    # Zenithal Hourly Rate: the IMO's idealised count, for a radiant
    # overhead under a perfectly dark sky. Real counts are always lower.
    zhr: int
    radiant_declination_deg: float


SHOWERS: tuple[MeteorShower, ...] = (
    MeteorShower("Quadrantids", "010 QUA", (12, 28), (1, 12), (1, 3), 80, 49.0),
    MeteorShower("April Lyrids", "006 LYR", (4, 14), (4, 30), (4, 22), 18, 34.0),
    MeteorShower("Eta Aquariids", "031 ETA", (4, 19), (5, 28), (5, 6), 50, -1.0),
    MeteorShower("Southern Delta Aquariids", "005 SDA", (7, 12), (8, 23), (7, 31), 25, -16.0),
    MeteorShower("Perseids", "007 PER", (7, 17), (8, 24), (8, 13), 100, 58.0),
    MeteorShower("Orionids", "008 ORI", (10, 2), (11, 7), (10, 21), 20, 16.0),
    MeteorShower("Leonids", "013 LEO", (11, 6), (11, 30), (11, 17), 15, 22.0),
    MeteorShower("Geminids", "004 GEM", (12, 4), (12, 20), (12, 14), 150, 33.0),
    MeteorShower("Ursids", "015 URS", (12, 17), (12, 26), (12, 22), 10, 76.0),
)


def rises_at(latitude_deg: float, radiant_declination_deg: float) -> bool:
    """Whether a radiant at this declination ever clears the horizon here.

    A radiant is permanently below the horizon when its declination is
    south of (latitude - 90). At Rømø's 55°N that rules out anything below
    about -35°, which is why the far-southern showers in the IMO table
    aren't listed above.
    """
    return radiant_declination_deg > latitude_deg - 90.0


def _as_number(month_day: tuple[int, int]) -> int:
    return month_day[0] * 100 + month_day[1]


def _within_period(day: date, start: tuple[int, int], end: tuple[int, int]) -> bool:
    """Whether a date falls in an activity period, which may wrap the year."""
    today = _as_number((day.month, day.day))
    first, last = _as_number(start), _as_number(end)
    if first <= last:
        return first <= today <= last
    # e.g. the Quadrantids, Dec 28 - Jan 12.
    return today >= first or today <= last


def _peak_date_near(day: date, peak: tuple[int, int]) -> date:
    """The shower's peak, resolved to whichever year is nearest `day`.

    Needed for year-wrapping showers: on 30 December the Quadrantid peak
    that matters is the one in January, not the one 364 days behind.
    """
    candidates = [
        date(day.year + offset, peak[0], peak[1])
        for offset in (-1, 0, 1)
        # Guard against 29 February never appearing in a peak, but keep
        # the code honest if a future table ever lists it.
        if _is_real_date(day.year + offset, peak)
    ]
    return min(candidates, key=lambda candidate: abs((candidate - day).days))


def _is_real_date(year: int, month_day: tuple[int, int]) -> bool:
    try:
        date(year, month_day[0], month_day[1])
    except ValueError:
        return False
    return True


def active_showers(on: date, latitude_deg: float) -> tuple[MeteorShower, ...]:
    """Showers active on this date, strongest first."""
    active = [
        shower
        for shower in SHOWERS
        if shower.zhr >= _WORTH_MENTIONING_ZHR
        and rises_at(latitude_deg, shower.radiant_declination_deg)
        and _within_period(on, shower.start, shower.end)
    ]
    return tuple(sorted(active, key=lambda shower: shower.zhr, reverse=True))


def describe(on: date, latitude_deg: float) -> str:
    """One line on tonight's meteor activity, or "" when there is none.

    Silence is deliberate: for much of the year no listed shower is
    running, and saying so every night would be filler.
    """
    showers = active_showers(on, latitude_deg)
    if not showers:
        return ""

    best = showers[0]
    peak = _peak_date_near(on, best.peak)
    days_to_peak = (peak - on).days

    if days_to_peak == 0:
        timing = "peaks tonight"
    elif days_to_peak == 1:
        timing = "peaks tomorrow night"
    elif days_to_peak > 1:
        timing = f"builds to a peak on {peak:%a %d %b}"
    elif days_to_peak == -1:
        timing = "peaked last night, still worth a look"
    else:
        timing = f"peaked {peak:%a %d %b}, tailing off"

    others = ""
    if len(showers) > 1:
        names = ", ".join(shower.name for shower in showers[1:])
        others = f" Also active: {names}."

    # "under ideal skies" is not hedging -- ZHR assumes the radiant
    # overhead and a perfectly dark sky, so the real count is always lower.
    return (
        f"\U0001f320 {best.name} {timing} — up to {best.zhr}/hour under ideal"
        f" skies, running to {date(on.year, *best.end):%d %b}.{others}"
    )
