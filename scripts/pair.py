"""One-time interactive pairing.

Run locally with `poetry run python scripts/pair.py`, then scan the QR code
printed in the terminal using WhatsApp on your phone
(Settings -> Linked Devices -> Link a Device).

Session credentials are saved to the sqlite file at SESSION_DB_PATH (default:
data/session.db) -- treat that file like a password. Never commit it; it is
what later gets base64-encoded into the WHATSAPP_SESSION_DB_B64 GitHub secret.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

from neonize.client import ClientFactory
from neonize.events import ConnectedEv

from romo_bot.config import DEFAULT_SESSION_DB_PATH

if TYPE_CHECKING:
    from neonize.client import NewClient

logging.basicConfig(level=logging.INFO)


def main() -> None:
    session_db_path = Path(os.environ.get("SESSION_DB_PATH", str(DEFAULT_SESSION_DB_PATH)))
    session_db_path.parent.mkdir(parents=True, exist_ok=True)

    factory = ClientFactory(database_name=str(session_db_path))
    client = factory.new_client()

    @client.event(ConnectedEv)  # type: ignore[untyped-decorator]  # neonize ships no stubs
    def _on_connected(_client: NewClient, _event: object) -> None:
        print(f"\nPaired successfully. Session saved to {session_db_path}")
        print("Press Ctrl+C now, then run: poetry run python scripts/list_groups.py\n")

    client.connect()


if __name__ == "__main__":
    main()
