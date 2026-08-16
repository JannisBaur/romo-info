from __future__ import annotations

from romo_bot.models import TideDirection, TideForecast, WeatherForecast

# Rømø's beach faces roughly west into the North Sea; wind from the SW
# through W to NW blows onshore, churning amber loose from the seabed and
# washing it up on the beach -- the well-known rule amber hunters already
# use, not a guess.
_ONSHORE_MIN_DEG = 202.5
_ONSHORE_MAX_DEG = 337.5
_STRONG_WIND_KMH = 25.0


class AmberAdvisor:
    """Suggests whether conditions favour amber hunting on Rømø's beach.

    Pure deterministic heuristic, no I/O and no external API: strong
    onshore wind is what washes amber ashore, and it's easiest to spot on
    the beach exposed around low tide.
    """

    def suggest(self, weather: WeatherForecast, tide: TideForecast) -> str:
        is_onshore = _ONSHORE_MIN_DEG <= weather.wind_direction_deg <= _ONSHORE_MAX_DEG
        is_strong = weather.wind_speed_max_kmh >= _STRONG_WIND_KMH
        low_tide_note = self._low_tide_note(tide)

        if is_onshore and is_strong:
            return (
                f"Good conditions — strong onshore wind "
                f"({weather.wind_speed_max_kmh:.0f} km/h).{low_tide_note}"
            )
        if is_strong:
            return f"Windy but not onshore, less likely today.{low_tide_note}"
        return f"Calm conditions, unlikely today.{low_tide_note}"

    @staticmethod
    def _low_tide_note(tide: TideForecast) -> str:
        low_tides = [e for e in tide.extremes if e.direction == TideDirection.LOW]
        if not low_tides:
            return ""
        earliest_low = min(low_tides, key=lambda e: e.at)
        return f" Best around low tide (~{earliest_low.at:%H:%M})."
