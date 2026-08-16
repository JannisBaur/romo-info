from __future__ import annotations

from romo_bot.models import TideDirection, TideExtreme, TideForecast, WeatherForecast

# Amber washes ashore on Denmark's North Sea coast in two phases: a storm
# (classically from the SW) loosens it from the seabed, then it's carried
# in during the calmer weather that follows -- not necessarily while the
# storm is still blowing. Today shouldn't itself be too rough to
# comfortably search.
_CALM_ENOUGH_WIND_KMH = 25.0

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
            note = f"Good conditions — recent onshore storm, calmer now.{low_tide_note}"
        elif weather.recent_onshore_storm:
            note = (
                f"Amber's likely loose from a recent storm, but it's still rough "
                f"({weather.wind_speed_max_kmh:.0f} km/h) — wait for calmer seas.{low_tide_note}"
            )
        else:
            note = (
                f"No onshore storm in the past few days, so unlikely regardless of "
                f"the {weather.wind_speed_max_kmh:.0f} km/h wind.{low_tide_note}"
            )

        if weather.upcoming_storm_date is not None:
            note += (
                f"\n\U0001f30a Onshore storm forecast {weather.upcoming_storm_date:%a %d %b}"
                " — worth checking again a day or two after."
            )
        return note

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
