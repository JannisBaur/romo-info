from __future__ import annotations

# Rømø's beaches (Lakolk, Sønderstrand) are on the island's west
# side, facing the North Sea, so the shore-normal points due west. Wind
# bearings are meteorological -- the direction wind blows *from* -- which
# makes 270 deg (W) dead-on onshore, and the band below is symmetric
# +/-67.5 deg around it: SSW through W to NNW. The edges are nearly
# alongshore rather than straight in, but a strong blow with any westerly
# component still drives sea against this coast, which is what stirs amber
# loose from the seabed.
_ONSHORE_MIN_DEG = 202.5  # SSW
_ONSHORE_MAX_DEG = 337.5  # NNW

_COMPASS_POINTS = (
    "N",
    "NNE",
    "NE",
    "ENE",
    "E",
    "ESE",
    "SE",
    "SSE",
    "S",
    "SSW",
    "SW",
    "WSW",
    "W",
    "WNW",
    "NW",
    "NNW",
)


def compass_point(degrees: float) -> str:
    """Bearing as a 16-point compass label, e.g. 250 -> "WSW"."""
    return _COMPASS_POINTS[round(degrees / 22.5) % 16]


def is_onshore(degrees: float) -> bool:
    """Whether wind from this bearing blows in off the sea at Rømø."""
    return _ONSHORE_MIN_DEG <= degrees <= _ONSHORE_MAX_DEG
