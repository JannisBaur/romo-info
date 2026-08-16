from __future__ import annotations

from pathlib import Path

import pytest

from romo_bot.config import ConfigError, Settings


def test_from_env_uses_defaults_for_optional_values() -> None:
    settings = Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us"})
    assert settings.whatsapp_group_jid == "123@g.us"
    assert settings.session_db_path == Path("data/session.db")
    assert settings.latitude == pytest.approx(55.13)
    assert settings.timezone == "Europe/Copenhagen"


def test_from_env_missing_group_jid_raises() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({})


def test_from_env_respects_overrides() -> None:
    settings = Settings.from_env(
        {
            "WHATSAPP_GROUP_JID": "123@g.us",
            "SESSION_DB_PATH": "custom/session.db",
            "LATITUDE": "1.5",
            "LONGITUDE": "2.5",
            "REPORT_TIMEZONE": "UTC",
        }
    )
    assert settings.session_db_path == Path("custom/session.db")
    assert settings.latitude == 1.5
    assert settings.longitude == 2.5
    assert settings.timezone == "UTC"


def test_from_env_invalid_latitude_raises_config_error() -> None:
    with pytest.raises(ConfigError):
        Settings.from_env({"WHATSAPP_GROUP_JID": "123@g.us", "LATITUDE": "not-a-number"})
