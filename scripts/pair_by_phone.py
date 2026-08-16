"""Pair using a typed-in code instead of a QR scan.

WhatsApp's QR pairing needs a second screen: one device showing the code,
another (with WhatsApp's camera) scanning it. This script uses WhatsApp's
alternative flow -- "Link with phone number instead" -- which only needs a
short code typed into the WhatsApp app, so it works from a single phone.

This must run somewhere with real internet access reaching WhatsApp's
servers (e.g. a GitHub Codespace opened from a phone browser -- see
README.md). It will not run inside a sandboxed environment that blocks
WhatsApp's domains.

Usage:
    WHATSAPP_PHONE_NUMBER=4512345678 poetry run python scripts/pair_by_phone.py

WHATSAPP_PHONE_NUMBER: your WhatsApp number with country code, digits only
(no "+", spaces, or dashes) -- e.g. 4512345678 for a Danish number.
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import time
from pathlib import Path
from typing import TYPE_CHECKING

from neonize.client import ClientFactory
from neonize.events import ConnectedEv
from neonize.exc import PairPhoneError

from romo_bot.config import DEFAULT_SESSION_DB_PATH

if TYPE_CHECKING:
    from neonize.client import NewClient

logging.basicConfig(level=logging.INFO)

_CONNECT_SETTLE_SECONDS = 3.0
_PAIR_REQUEST_ATTEMPTS = 3
# ClientFactory.new_client() requires a jid (reconnecting) or a uuid
# (first-time pairing) -- any stable string works, it just has to be unique
# within this session db.
_PAIRING_CLIENT_UUID = "romo-bot"


def main() -> None:
    phone = os.environ.get("WHATSAPP_PHONE_NUMBER")
    if not phone:
        sys.exit("Set WHATSAPP_PHONE_NUMBER (country code + number, digits only) first.")

    session_db_path = Path(os.environ.get("SESSION_DB_PATH", str(DEFAULT_SESSION_DB_PATH)))
    session_db_path.parent.mkdir(parents=True, exist_ok=True)

    factory = ClientFactory(database_name=str(session_db_path))
    client = factory.new_client(uuid=_PAIRING_CLIENT_UUID)

    @client.event(ConnectedEv)  # type: ignore[untyped-decorator]  # neonize ships no stubs
    def _on_connected(_client: NewClient, _event: object) -> None:
        print(f"\nPaired successfully. Session saved to {session_db_path}")
        print("Press Ctrl+C now, then run: poetry run python scripts/list_groups.py\n")

    # neonize's connect() blocks the calling thread until stop(), so the
    # pairing-code request has to happen from a second thread while the
    # connection is being established.
    connect_thread = threading.Thread(target=client.connect, daemon=True)
    connect_thread.start()
    time.sleep(_CONNECT_SETTLE_SECONDS)

    code: str | None = None
    last_error: PairPhoneError | None = None
    for _attempt in range(_PAIR_REQUEST_ATTEMPTS):
        try:
            code = client.PairPhone(phone, show_push_notification=True)
            break
        except PairPhoneError as exc:
            last_error = exc
            time.sleep(2.0)

    if code is None:
        sys.exit(f"Could not request a pairing code: {last_error}")

    print("\nOn your phone: WhatsApp -> Settings -> Linked Devices -> Link a Device")
    print(f"-> 'Link with phone number instead' -> enter this code:\n\n    {code}\n")

    connect_thread.join()


if __name__ == "__main__":
    main()
