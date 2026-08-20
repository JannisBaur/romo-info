from __future__ import annotations

from datetime import date

from romo_info.meteors import (
    SHOWERS,
    active_showers,
    describe,
    rises_at,
)

_ROMO_LAT = 55.13


def test_every_listed_shower_is_visible_from_romo() -> None:
    # The IMO table includes far-southern radiants; any that can never
    # clear the horizon here should have been left out of the list.
    assert all(rises_at(_ROMO_LAT, s.radiant_declination_deg) for s in SHOWERS)


def test_far_southern_radiants_never_rise_here() -> None:
    # Puppid-Velids (-45) and alpha-Centaurids (-58) from the IMO table.
    assert rises_at(_ROMO_LAT, -45.0) is False
    assert rises_at(_ROMO_LAT, -58.0) is False
    assert rises_at(_ROMO_LAT, 16.0) is True


def test_perseids_are_active_in_mid_august() -> None:
    # IMO Table 5: Perseids run Jul 17 - Aug 24.
    names = [s.name for s in active_showers(date(2026, 8, 19), _ROMO_LAT)]

    assert "Perseids" in names


def test_perseids_are_over_by_september() -> None:
    names = [s.name for s in active_showers(date(2026, 9, 1), _ROMO_LAT)]

    assert "Perseids" not in names


def test_quadrantid_period_wraps_the_new_year() -> None:
    # Dec 28 - Jan 12, so it must be active on both sides of midnight
    # on the 31st and dead in between.
    assert "Quadrantids" in [s.name for s in active_showers(date(2026, 12, 30), _ROMO_LAT)]
    assert "Quadrantids" in [s.name for s in active_showers(date(2026, 1, 5), _ROMO_LAT)]
    assert "Quadrantids" not in [s.name for s in active_showers(date(2026, 6, 1), _ROMO_LAT)]


def test_strongest_shower_is_reported_first() -> None:
    # Mid-August has both the Perseids (ZHR 100) and the Southern Delta
    # Aquariids (ZHR 25) running.
    showers = active_showers(date(2026, 8, 19), _ROMO_LAT)

    assert len(showers) >= 2
    assert showers[0].name == "Perseids"


def test_quiet_stretch_says_nothing_at_all() -> None:
    # Early March has no listed shower; filler would be worse than silence.
    assert describe(date(2026, 3, 5), _ROMO_LAT) == ""


def test_peak_night_is_called_out() -> None:
    note = describe(date(2026, 8, 13), _ROMO_LAT)

    assert "Perseids peaks tonight" in note
    assert "100/hour" in note


def test_after_the_peak_reads_as_tailing_off() -> None:
    note = describe(date(2026, 8, 19), _ROMO_LAT)

    assert "peaked" in note
    assert "tailing off" in note


def test_before_the_peak_reads_as_building() -> None:
    note = describe(date(2026, 12, 6), _ROMO_LAT)

    assert "Geminids" in note
    assert "builds to a peak" in note


def test_zhr_is_qualified_as_an_ideal_figure() -> None:
    # ZHR assumes a radiant overhead under a perfect sky; quoting it bare
    # would promise counts nobody gets.
    note = describe(date(2026, 8, 13), _ROMO_LAT)

    assert "under ideal" in note


def test_secondary_showers_are_mentioned_after_the_main_one() -> None:
    note = describe(date(2026, 8, 19), _ROMO_LAT)

    assert "Also active" in note
    assert "Southern Delta Aquariids" in note
