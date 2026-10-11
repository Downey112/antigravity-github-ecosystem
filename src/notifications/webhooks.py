"""Generic Webhooks Dispatcher Module.

Delivers structured JSON events to external monitoring, incident response,
or communication systems (SMS, email, PagerDuty, custom webhook receivers).
"""

import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional
import httpx

from src.config import settings

logger = logging.getLogger("WebhooksDispatcher")

class WebhookDispatcher:
    """Dispatches cryptographically signed payloads to external webhooks."""

    def __init__(self):
        self.endpoint = settings.OUTBOUND_WEBHOOK_URL
        self.secret_key = settings.WEBHOOK_SECRET_KEY

    def _generate_signature(self, payload_bytes: bytes) -> str:
        """Generates HMAC SHA256 signature for payload verification."""
        if not self.secret_key:
            return ""
        return hmac.new(self.secret_key.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()

    async def emit_event(self, event_type: str, data: Dict[str, Any]) -> bool:
        """Sends an event payload to the configured webhook."""
        if not self.endpoint:
            logger.debug(f"[Webhook Skipped] No endpoint configured for event: {event_type}")
            return True

        envelope = {
            "event": event_type,
            "timestamp": int(time.time()),
            "environment": settings.ENV,
            "data": data,
        }
        body = json.dumps(envelope)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Antigravity-Agent-Ecosystem/1.0",
        }
        sig = self._generate_signature(body.encode("utf-8"))
        if sig:
            headers["X-Antigravity-Signature"] = sig

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.endpoint, content=body, headers=headers)
                return res.status_code in (200, 201, 202, 204)
        except Exception as e:
            logger.error(f"Failed to post webhook event '{event_type}': {e}")
            return False

webhook_dispatcher = WebhookDispatcher()
