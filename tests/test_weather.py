from __future__ import annotations

from romo_info.weather import (
    _ONSHORE_MAX_DEG,
    _ONSHORE_MIN_DEG,
    compass_point,
    is_onshore,
)


def test_compass_point_labels_cardinal_bearings() -> None:
    assert compass_point(0.0) == "N"
    assert compass_point(90.0) == "E"
    assert compass_point(180.0) == "S"
    assert compass_point(270.0) == "W"


def test_compass_point_labels_intermediate_bearings() -> None:
    assert compass_point(250.0) == "WSW"
    assert compass_point(225.0) == "SW"


def test_compass_point_wraps_past_north() -> None:
    # 350 deg is nearer N than NNW, and must not index off the end.
    assert compass_point(350.0) == "N"
    assert compass_point(360.0) == "N"


def test_onshore_matches_westerly_bearings() -> None:
    assert is_onshore(250.0) is True  # WSW, in off the sea
    assert is_onshore(270.0) is True  # due W
    assert is_onshore(90.0) is False  # due E, off the land


def test_onshore_boundaries_are_inclusive() -> None:
    assert is_onshore(202.5) is True
    assert is_onshore(337.5) is True
    assert is_onshore(202.4) is False
    assert is_onshore(337.6) is False


def test_onshore_band_is_centred_on_due_west() -> None:
    # Rømø's beaches face west, so the shore-normal is 270 deg and
    # the band must sit symmetrically around it -- a band centred anywhere
    # else would be describing a different coastline.
    centre = (_ONSHORE_MIN_DEG + _ONSHORE_MAX_DEG) / 2
    assert centre == 270.0
    assert compass_point(centre) == "W"


def test_offshore_bearings_are_rejected() -> None:
    # Due east is straight off the Wadden Sea side, and north/south run
    # along the coast rather than into it.
    assert is_onshore(90.0) is False
    assert is_onshore(0.0) is False
    assert is_onshore(180.0) is False
