from __future__ import annotations

from datetime import date
from zoneinfo import ZoneInfo

import pytest

from romo_info.clients.dmi_tide import DmiTideTableError, extremes_for_date, parse_table
from romo_info.models import TideDirection

_UTC = ZoneInfo("UTC")

# Three full days so the middle day (Aug 15, our target in tests below) has
# real neighbours on both sides -- extrema detection needs a point before
# and after to classify a peak/trough, so a day at the very edge of a
# fixture can't have its boundary extremes classified. Values are made up,
# just alternating high/low as a real semidiurnal tide does.
_SAMPLE_TABLE = """\
# TIDE TABLE
# Time Zone:    Danish standard time [UTC +1 hour]
#---------------------------------------------------------
202608140500 180.0
202608141100  10.0
202608141700 190.0
202608142300   0.0
202608150500 185.0
202608151100  -5.0
202608151700 195.0
202608152300  -8.0
202608160500 183.0
202608161100   5.0
202608161700 188.0
202608162300   2.0
"""


def test_parse_table_skips_comments_and_converts_timezone() -> None:
    entries = parse_table(_SAMPLE_TABLE, target_timezone=_UTC)

    assert len(entries) == 12
    # Table time is fixed UTC+1; converting to UTC subtracts one hour.
    first_at, first_height = entries[0]
    assert first_at.hour == 4
    assert first_height == 180.0


def test_parse_table_rejects_malformed_line() -> None:
    with pytest.raises(DmiTideTableError):
        parse_table("not a valid line\n", target_timezone=_UTC)


def test_extremes_for_date_classifies_high_and_low_in_cm_to_m() -> None:
    entries = parse_table(_SAMPLE_TABLE, target_timezone=_UTC)

    forecast = extremes_for_date(entries, date(2026, 8, 15))

    assert [e.direction for e in forecast.extremes] == [
        TideDirection.HIGH,
        TideDirection.LOW,
        TideDirection.HIGH,
        TideDirection.LOW,
    ]
    assert forecast.extremes[0].height_m == pytest.approx(1.85)
    assert all(e.at.date() == date(2026, 8, 15) for e in forecast.extremes)


def test_extremes_for_date_raises_when_date_not_covered() -> None:
    entries = parse_table(_SAMPLE_TABLE, target_timezone=_UTC)

    with pytest.raises(DmiTideTableError):
        extremes_for_date(entries, date(2030, 1, 1))
