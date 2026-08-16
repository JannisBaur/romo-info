from __future__ import annotations

from romo_bot.models import StormOutlook, TideDirection, TideExtreme, TideForecast, WeatherForecast

# Amber washes ashore on Denmark's North Sea coast in two phases: a storm
# (classically from the SW) loosens it from the seabed, then it's carried
# in during the calmer weather that follows -- not necessarily while the
# storm is still blowing. Today shouldn't itself be too rough to
# comfortably search. 10 m/s (~36 km/h) as the "calm enough" cutoff is
# corroborated by multiple independent Danish amber-hunting sources
# (ravjagt.dk, ravvejr.dk, ravfund.dk) -- see _STORM_WIND_KMH in weather.py
# for the matching "strong enough to stir the seabed" threshold.
_CALM_ENOUGH_WIND_KMH = 36.0

# Prefer suggesting a low tide that falls at a sensible hour to actually
# go outside, rather than technically-correct-but-useless "best time: 3am".
_REASONABLE_HOUR_START = 6
_REASONABLE_HOUR_END = 21


class AmberAdvisor:
    """Suggests whether conditions favour amber hunting on Rømø's beach.

    Pure deterministic heuristic, no I/O and no external API. See
    romo_bot.weather.had_recent_onshore_storm for the storm-detection side
    of this (checked over the past few days, not just today -- today's own
    wind, however strong, does not by itself count as "recent").
    """

    def suggest(self, weather: WeatherForecast, tide: TideForecast) -> str:
        is_calm_enough_today = weather.wind_speed_max_kmh <= _CALM_ENOUGH_WIND_KMH
        low_tide_note = self._low_tide_note(tide)

        if weather.recent_onshore_storm and is_calm_enough_today:
            return f"Good conditions — recent onshore storm, calmer now.{low_tide_note}"
        if weather.recent_onshore_storm:
            return (
                f"Amber's likely loose from a recent storm, but it's still rough "
                f"({weather.wind_speed_max_kmh:.0f} km/h) — wait for calmer seas.{low_tide_note}"
            )
        return (
            f"No onshore storm in the past {weather.recent_storm_lookback_days} days, so "
            f"unlikely regardless of the {weather.wind_speed_max_kmh:.0f} km/h wind.{low_tide_note}"
        )

    @staticmethod
    def describe_outlook(outlook: StormOutlook) -> str:
        """A single, report-wide heads-up on any onshore storm forecast in
        the next few days -- distinct from suggest()'s per-day verdict,
        which only looks *backward* at whether a storm already happened.
        """
        if outlook.upcoming_storm_date is not None:
            return (
                f"\U0001f52e Storm forecast {outlook.upcoming_storm_date:%a %d %b}"
                " — worth checking again a day or two after that."
            )
        return f"\U0001f52e No storm forecast through {outlook.lookahead_through:%a %d %b}."

    @staticmethod
    def _low_tide_note(tide: TideForecast) -> str:
        low_tides = [e for e in tide.extremes if e.direction == TideDirection.LOW]
        if not low_tides:
            return ""

        daytime_lows = [
            e for e in low_tides if _REASONABLE_HOUR_START <= e.at.hour < _REASONABLE_HOUR_END
        ]
        if daytime_lows:
            best = min(daytime_lows, key=lambda e: e.at)
            return f" Best around low tide (~{best.at:%H:%M})."

        # Every low tide that day falls overnight -- worth mentioning, but
        # don't imply it's actually a good time to go stand on the beach.
        overnight: TideExtreme = min(low_tides, key=lambda e: e.at)
        return f" Low tide is overnight (~{overnight.at:%H:%M}), not at a practical hour."
