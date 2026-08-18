from __future__ import annotations

import math
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from romo_info.models import StargazingForecast

# Mean synodic month -- new moon to new moon.
_SYNODIC_MONTH_DAYS = 29.530588853
# A known new moon to count from (2000 Jan 6, 18:14 UTC).
_REFERENCE_NEW_MOON = datetime(2000, 1, 6, 18, 14, tzinfo=UTC)

# Cloud cover, averaged across the dark hours, above which there's no point
# going outside.
_OVERCAST_PCT = 70
_CLEAR_PCT = 30
# Above this the moon washes out the Milky Way and anything faint. It
# doesn't stop you seeing planets and bright constellations, so it's a
# caveat rather than a veto.
_BRIGHT_MOON_PCT = 60
# Nobody is realistically out past this, so the window stops here rather
# than running to sunrise -- averaging cloud over hours you'd be asleep
# for makes the number describe a night you aren't having.
_LATEST_PRACTICAL_HOUR = 2
# Only name the clearest hour when it's meaningfully better than the
# night's average; on a uniformly overcast night it's just noise.
_CLEARER_BY_PCT = 15


def moon_illumination_fraction(at: datetime) -> float:
    """Fraction of the moon's disc lit, 0.0 (new) to 1.0 (full).

    Pure and deterministic -- a mean-synodic-month approximation, so it can
    be a percent or two off around the quarters. That's far finer than the
    question being asked ("will moonlight drown out the sky tonight?"), and
    it avoids an ephemeris dependency for one number.
    """
    if at.tzinfo is None:
        raise ValueError("moon_illumination_fraction needs an aware datetime")
    elapsed_days = (at - _REFERENCE_NEW_MOON).total_seconds() / 86400.0
    phase = (elapsed_days % _SYNODIC_MONTH_DAYS) / _SYNODIC_MONTH_DAYS
    return (1.0 - math.cos(2.0 * math.pi * phase)) / 2.0


def moon_phase_name(at: datetime) -> str:
    """Conventional name for where the moon is in its cycle."""
    if at.tzinfo is None:
        raise ValueError("moon_phase_name needs an aware datetime")
    elapsed_days = (at - _REFERENCE_NEW_MOON).total_seconds() / 86400.0
    phase = (elapsed_days % _SYNODIC_MONTH_DAYS) / _SYNODIC_MONTH_DAYS
    if phase < 0.02 or phase >= 0.98:
        return "new moon"
    if phase < 0.23:
        return "waxing crescent"
    if phase < 0.27:
        return "first quarter"
    if phase < 0.48:
        return "waxing gibbous"
    if phase < 0.52:
        return "full moon"
    if phase < 0.73:
        return "waning gibbous"
    if phase < 0.77:
        return "last quarter"
    return "waning crescent"


def mean_cloud_cover(
    timestamps: Sequence[datetime],
    cloud_cover_pct: Sequence[float],
    start: datetime,
    end: datetime,
) -> float | None:
    """Average cloud cover across the hours between start and end.

    Returns None when the window isn't covered by the data at all, so the
    caller can say so rather than quietly reporting a clear sky.
    """
    if len(timestamps) != len(cloud_cover_pct):
        raise ValueError("timestamps and cloud_cover_pct must be the same length")
    within = [
        cover for at, cover in zip(timestamps, cloud_cover_pct, strict=True) if start <= at <= end
    ]
    if not within:
        return None
    return sum(within) / len(within)


def clearest_hour(
    timestamps: Sequence[datetime],
    cloud_cover_pct: Sequence[float],
    start: datetime,
    end: datetime,
) -> tuple[datetime, float] | None:
    """The least cloudy hour in the window, if the window has any hours.

    A mean alone can't distinguish "hazy all night" from "closes in after
    midnight", and those call for different plans.
    """
    if len(timestamps) != len(cloud_cover_pct):
        raise ValueError("timestamps and cloud_cover_pct must be the same length")
    within = [
        (at, cover)
        for at, cover in zip(timestamps, cloud_cover_pct, strict=True)
        if start <= at <= end
    ]
    if not within:
        return None
    return min(within, key=lambda hour_and_cover: hour_and_cover[1])


def describe(forecast: StargazingForecast | None) -> str:
    """One line on whether tonight is worth going out for."""
    if forecast is None or forecast.cloud_cover_pct is None:
        return "\U0001f30c Tonight's cloud forecast is unavailable."

    # Deliberately not "Dark 21:38-02:00": darkness doesn't end at 02:00,
    # that's just where we stop looking (see night_window). Saying it as a
    # range read as though the sky brightened again at two in the morning.
    starts = f"Dark from {forecast.darkness_from:%H:%M}"
    cover = forecast.cloud_cover_pct
    moon = forecast.moon_illumination_pct
    moon_note = f"moon {moon}% ({forecast.moon_phase})"

    if cover >= _OVERCAST_PCT:
        verdict = "mostly clouded out"
    elif cover <= _CLEAR_PCT and moon <= _BRIGHT_MOON_PCT:
        verdict = "good, dark and mostly clear"
    elif cover <= _CLEAR_PCT:
        verdict = "clear, but moonlight will wash out anything faint"
    else:
        verdict = "broken cloud, worth a look but patchy"

    best = ""
    if (
        forecast.clearest_at is not None
        and forecast.clearest_cover_pct is not None
        and forecast.clearest_cover_pct + _CLEARER_BY_PCT <= cover
    ):
        best = (
            f" Clearest around {forecast.clearest_at:%H:%M}" f" ({forecast.clearest_cover_pct}%)."
        )

    return (
        f"\U0001f30c {starts} · {cover}% cloud until "
        f"{forecast.darkness_to:%H:%M} · {moon_note} — {verdict}.{best}"
    )


def build_forecast(
    *,
    darkness_from: datetime,
    darkness_to: datetime,
    timestamps: Sequence[datetime],
    cloud_cover_pct: Sequence[float],
) -> StargazingForecast:
    """Assemble tonight's viewing conditions from the hourly cloud series."""
    mean_cover = mean_cloud_cover(timestamps, cloud_cover_pct, darkness_from, darkness_to)
    best = clearest_hour(timestamps, cloud_cover_pct, darkness_from, darkness_to)
    # Judge the moon at the middle of the night rather than at sunset, so a
    # moon that rises late isn't reported as though it were up all night.
    midnight = darkness_from + (darkness_to - darkness_from) / 2
    return StargazingForecast(
        darkness_from=darkness_from,
        darkness_to=darkness_to,
        cloud_cover_pct=None if mean_cover is None else round(mean_cover),
        moon_illumination_pct=round(moon_illumination_fraction(midnight) * 100),
        moon_phase=moon_phase_name(midnight),
        clearest_at=None if best is None else best[0],
        clearest_cover_pct=None if best is None else round(best[1]),
    )


def night_window(sunset: datetime, next_sunrise: datetime) -> tuple[datetime, datetime]:
    """The window you'd realistically be out in.

    Sunset isn't darkness -- it stays too bright to see much for a while
    after, and brightens again well before sunrise -- so both ends are
    nudged in by twilight. The end is then capped at _LATEST_PRACTICAL_HOUR,
    because a summer night here runs to nearly 04:00 and nobody is standing
    outside for it; including those hours would average in weather nobody
    is going to see.
    """
    twilight = timedelta(minutes=45)
    start = sunset + twilight
    end = next_sunrise - twilight

    cutoff = (start + timedelta(days=1)).replace(
        hour=_LATEST_PRACTICAL_HOUR, minute=0, second=0, microsecond=0
    )
    # Only apply the cap when it still leaves a usable window -- in deep
    # winter darkness starts long before 02:00, but the guard keeps this
    # honest if the arithmetic ever lands the other way round.
    if start < cutoff < end:
        end = cutoff
    return start, end
