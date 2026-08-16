from __future__ import annotations

from romo_bot.models import TideDirection, TideForecast, WeatherForecast

# Amber washes ashore on Denmark's North Sea coast in two phases: a storm
# (classically from the SW) loosens it from the seabed, then it's carried
# in during the calmer weather that follows -- not necessarily while the
# storm is still blowing. Today shouldn't itself be too rough to
# comfortably search.
_CALM_ENOUGH_WIND_KMH = 25.0


class AmberAdvisor:
    """Suggests whether conditions favour amber hunting on Rømø's beach.

    Pure deterministic heuristic, no I/O and no external API. See
    romo_bot.weather.had_recent_onshore_storm for the storm-detection side
    of this (checked over the past few days, not just today).
    """

    def suggest(self, weather: WeatherForecast, tide: TideForecast) -> str:
        is_calm_enough_today = weather.wind_speed_max_kmh <= _CALM_ENOUGH_WIND_KMH
        low_tide_note = self._low_tide_note(tide)

        if weather.recent_onshore_storm and is_calm_enough_today:
            return f"Good conditions — recent onshore storm, calmer today.{low_tide_note}"
        if weather.recent_onshore_storm:
            return (
                f"Amber may be loose from a recent storm, but it's still rough — "
                f"wait for calmer seas.{low_tide_note}"
            )
        return f"No recent storm to loosen amber, less likely today.{low_tide_note}"

    @staticmethod
    def _low_tide_note(tide: TideForecast) -> str:
        low_tides = [e for e in tide.extremes if e.direction == TideDirection.LOW]
        if not low_tides:
            return ""
        earliest_low = min(low_tides, key=lambda e: e.at)
        return f" Best around low tide (~{earliest_low.at:%H:%M})."
