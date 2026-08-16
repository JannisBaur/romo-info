from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from neonize.client import ClientFactory
from neonize.events import ConnectedEv, ConnectFailureEv
from neonize.exc import NeonizeError, SendMessageError
from neonize.proto.Neonize_pb2 import JID

if TYPE_CHECKING:
    from neonize.client import NewClient

logger = logging.getLogger(__name__)


class WhatsAppSessionError(RuntimeError):
    """Raised when no paired WhatsApp session exists yet."""


class WhatsAppSendError(RuntimeError):
    """Raised when a message could not be delivered."""


def _parse_group_jid(raw: str) -> JID:
    user, _, server = raw.partition("@")
    if not user or not server:
        raise ValueError(f"Invalid WhatsApp group JID: {raw!r}. Expected '<id>@g.us'.")
    return JID(User=user, Server=server, Device=0, Integrator=0, IsEmpty=False, RawAgent=0)


class NeonizeMessageSender:
    """Sends WhatsApp messages using a previously-paired Neonize session.

    Pairing (the interactive QR-code step) is deliberately not part of this
    class -- see scripts/pair.py. This class only ever reconnects an
    existing session, so it fails fast if none exists rather than hanging
    an unattended job on a QR code nobody can scan.
    """

    def __init__(self, session_db_path: Path) -> None:
        session_db_path.parent.mkdir(parents=True, exist_ok=True)
        self._factory = ClientFactory(database_name=str(session_db_path))

    def send(self, group_jid: str, text: str) -> None:
        devices = self._factory.get_all_devices()
        if not devices:
            raise WhatsAppSessionError(
                f"No paired WhatsApp session found at {self._factory.database_name!r}. "
                "Run scripts/pair.py locally first."
            )
        client = self._factory.new_client(jid=devices[0].JID)
        target = _parse_group_jid(group_jid)
        outcome: dict[str, BaseException | None] = {"error": None}

        # neonize ships no type stubs, so its decorator is untyped (Any) --
        # see the mypy override for neonize.* in pyproject.toml.
        @client.event(ConnectedEv)  # type: ignore[untyped-decorator]
        def _on_connected(connected_client: NewClient, _event: object) -> None:
            try:
                connected_client.send_message(target, text)
            except SendMessageError as exc:
                outcome["error"] = exc
            finally:
                connected_client.stop()

        @client.event(ConnectFailureEv)  # type: ignore[untyped-decorator]
        def _on_connect_failure(failed_client: NewClient, event: object) -> None:
            outcome["error"] = WhatsAppSendError(f"WhatsApp connection failed: {event}")
            failed_client.stop()

        try:
            client.connect()
        except NeonizeError as exc:
            raise WhatsAppSendError(f"WhatsApp connect() failed: {exc}") from exc

        error = outcome["error"]
        if error is not None:
            raise WhatsAppSendError(str(error)) from error
