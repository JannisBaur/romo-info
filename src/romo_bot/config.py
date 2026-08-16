from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_SESSION_DB_PATH = Path("data/session.db")
DEFAULT_LATITUDE = 55.13
DEFAULT_LONGITUDE = 8.45
DEFAULT_TIMEZONE = "Europe/Copenhagen"
# How many days to fully report (tide, weather, amber note) each run,
# starting today. Kept small by default to keep the message short --
# override with DAYS_TO_REPORT for a longer look (e.g. 2 for today +
# tomorrow, as earlier versions of this bot always did).
DEFAULT_DAYS_TO_REPORT = 1


class ConfigError(RuntimeError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    whatsapp_group_jid: str
    session_db_path: Path
    latitude: float
    longitude: float
    timezone: str
    days_to_report: int

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> Settings:
        source = env if env is not None else dict(os.environ)
        try:
            days_to_report = int(source.get("DAYS_TO_REPORT", str(DEFAULT_DAYS_TO_REPORT)))
            if days_to_report < 1:
                raise ConfigError(f"DAYS_TO_REPORT must be at least 1, got {days_to_report}")
            return cls(
                whatsapp_group_jid=_require(source, "WHATSAPP_GROUP_JID"),
                session_db_path=Path(source.get("SESSION_DB_PATH", str(DEFAULT_SESSION_DB_PATH))),
                latitude=float(source.get("LATITUDE", str(DEFAULT_LATITUDE))),
                longitude=float(source.get("LONGITUDE", str(DEFAULT_LONGITUDE))),
                timezone=source.get("REPORT_TIMEZONE", DEFAULT_TIMEZONE),
                days_to_report=days_to_report,
            )
        except ValueError as exc:
            raise ConfigError(f"Invalid configuration value: {exc}") from exc


def _require(source: dict[str, str], key: str) -> str:
    value = source.get(key)
    if not value:
        raise ConfigError(f"Missing required environment variable: {key}")
    return value
