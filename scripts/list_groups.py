"""Lists WhatsApp groups the paired account has joined, with their JIDs.

Run after scripts/pair.py to find the value to put in the WHATSAPP_GROUP_JID
secret: copy the '<id>@g.us' shown next to the group you want.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from neonize.client import ClientFactory
from neonize.events import ConnectedEv

from romo_bot.config import DEFAULT_SESSION_DB_PATH

if TYPE_CHECKING:
    from neonize.client import NewClient

logging.basicConfig(level=logging.WARNING)


def main() -> None:
    session_db_path = Path(os.environ.get("SESSION_DB_PATH", str(DEFAULT_SESSION_DB_PATH)))
    factory = ClientFactory(database_name=str(session_db_path))
    devices = factory.get_all_devices()
    if not devices:
        sys.exit("No paired session found. Run scripts/pair.py first.")

    client = factory.new_client(jid=devices[0].JID)

    @client.event(ConnectedEv)  # type: ignore[untyped-decorator]  # neonize ships no stubs
    def _on_connected(connected_client: NewClient, _event: object) -> None:
        print("\nJoined groups:\n")
        for group in connected_client.get_joined_groups():
            print(f"  {group.GroupName!r:40} {group.JID.User}@{group.JID.Server}")
        print("\nCopy the '<id>@g.us' value into the WHATSAPP_GROUP_JID secret.\n")
        connected_client.stop()

    client.connect()


if __name__ == "__main__":
    main()
