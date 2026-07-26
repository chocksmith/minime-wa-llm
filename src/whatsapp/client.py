from __future__ import annotations

from typing import Optional

from gowa_sdk import GoWaClient

from .jid import JID, parse_jid


class WhatsAppClient(GoWaClient):
    """Thin wrapper over GoWaClient for app-specific helpers."""

    _jid: Optional[JID] = None

    async def get_my_jid(self) -> JID:
        if self._jid:
            return self._jid

        # GOWA v8 repurposed /app/devices' `device` field to hold the
        # internal device UUID instead of the WhatsApp JID. The `/devices`
        # endpoint (list_devices) is v8's multi-device management API and
        # still exposes the real JID via `.jid`.
        info = await self.list_devices()
        if not info.results:
            raise ValueError("No devices found")
        device_jid = info.results[0].jid
        if not device_jid:
            raise ValueError("No primary device JID found")
        self._jid = parse_jid(device_jid)
        return self._jid
