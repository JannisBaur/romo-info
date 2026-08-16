from __future__ import annotations

import importlib.resources
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from romo_info.models import TideExtreme, TideForecast
from romo_info.tide import find_tide_extremes

# DMI publishes table timestamps in fixed Danish Standard Time (UTC+1)
# year-round, regardless of daylight saving -- not the actual civil
# Europe/Copenhagen clock, which is UTC+2 for most of the year. Every
# parsed timestamp below is first anchored to this fixed offset, then
# converted to the caller's real target timezone.
_TABLE_FIXED_OFFSET = timezone(timedelta(hours=1))


class DmiTideTableError(RuntimeError):
    """Raised when the bundled DMI tide table can't be read or parsed."""


def parse_table(text: str, *, target_timezone: ZoneInfo) -> list[tuple[datetime, float]]:
    """Parses a DMI '<yyyymmddHHMM> <height_cm>' tide table into
    (local datetime, height_cm) pairs, converted to target_timezone.
    """
    entries: list[tuple[datetime, float]] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            timestamp_str, height_str = line.split()
            naive = datetime.strptime(timestamp_str, "%Y%m%d%H%M")
        except ValueError as exc:
            raise DmiTideTableError(f"Unrecognised tide table line: {line!r}") from exc
        fixed_offset_dt = naive.replace(tzinfo=_TABLE_FIXED_OFFSET)
        entries.append((fixed_offset_dt.astimezone(target_timezone), float(height_str)))
    return entries


def extremes_for_date(entries: list[tuple[datetime, float]], target_date: date) -> TideForecast:
    """Pure: picks out target_date's high/low tide events from a full
    table of (already extrema) entries, given a day of surrounding
    context so boundary events are classified correctly.
    """
    window = [(at, cm) for at, cm in entries if abs((at.date() - target_date).days) <= 1]
    if not window:
        raise DmiTideTableError(f"No tide table entries found near {target_date}")

    timestamps = [at for at, _ in window]
    heights_cm = [cm for _, cm in window]
    all_extremes = find_tide_extremes(timestamps, heights_cm)
    todays = [e for e in all_extremes if e.at.date() == target_date]
    return TideForecast(
        extremes=tuple(
            TideExtreme(at=e.at, height_m=e.height_m / 100.0, direction=e.direction) for e in todays
        )
    )


class DmiTideTableClient:
    """Reads today's tide extremes from a bundled DMI harmonic tide table.

    DMI publishes one static, precomputed file per station per year
    listing every high/low water event -- no live API call, so this has
    no network dependency and can't be rate-limited (unlike DMI's live
    ocean-model API, which turned out to be unreliable from shared cloud
    IPs). The table is the real station-calibrated harmonic prediction,
    not a generic ocean model, so it matches official tide tables far
    more closely than a coarse global model can.

    The table only covers one calendar year; past December 31st of that
    year this raises DmiTideTableError, at which point the resource file
    needs replacing with the next year's table (see README.md).
    """

    def __init__(self, table_filename: str = "havneby_tides_2026.txt", *, timezone: str) -> None:
        self._table_filename = table_filename
        self._timezone = ZoneInfo(timezone)

    def fetch_tide_forecast(self, days: int) -> tuple[TideForecast, ...]:
        text = (
            importlib.resources.files("romo_info")
            .joinpath("data", self._table_filename)
            .read_text(encoding="utf-8")
        )
        entries = parse_table(text, target_timezone=self._timezone)
        today = datetime.now(self._timezone).date()
        return tuple(
            extremes_for_date(entries, today + timedelta(days=offset)) for offset in range(days)
        )
