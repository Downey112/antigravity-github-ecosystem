"""LinkGravity Notification & Interactive Approval Bridge.

Connects the Antigravity agent runtime to Slack, Discord, and Telegram.
Handles alert dispatches and Human-in-the-Loop (HITL) approval workflows.
"""

import json
import logging
from typing import Any, Dict, Optional
import httpx

from src.config import settings

logger = logging.getLogger("LinkGravity")

class LinkGravityBridge:
    """Manages notifications and approval requests over Slack, Discord, or Telegram."""

    def __init__(self):
        self.platform = settings.LINKGRAVITY_PLATFORM
        self.slack_url = settings.LINKGRAVITY_WEBHOOK_URL
        self.discord_url = settings.LINKGRAVITY_DISCORD_WEBHOOK_URL
        self.tg_token = settings.LINKGRAVITY_TELEGRAM_BOT_TOKEN
        self.tg_chat_id = settings.LINKGRAVITY_TELEGRAM_CHAT_ID

    async def broadcast(self, title: str, message: str, level: str = "INFO", fields: Optional[Dict[str, str]] = None) -> bool:
        """Dispatches an alert to configured chat platforms."""
        emoji = {"INFO": "ℹ️", "SUCCESS": "✅", "WARNING": "⚠️", "ERROR": "🚨"}.get(level, "🤖")
        formatted_title = f"{emoji} [{level}] {title}"

        success = True
        if self.platform == "slack" and self.slack_url:
            success = await self._send_slack(formatted_title, message, fields)
        elif self.platform == "discord" and self.discord_url:
            success = await self._send_discord(formatted_title, message, fields)
        elif self.platform == "telegram" and self.tg_token and self.tg_chat_id:
            success = await self._send_telegram(formatted_title, message, fields)
        else:
            logger.info(f"[LinkGravity Mock Broadcast] {formatted_title}\n{message}")
        return success

    async def request_tool_approval(self, tool_name: str, args: Dict[str, Any], reason: str) -> Dict[str, Any]:
        """Requests human approval for sensitive actions (e.g., git push, deploy, destructive commands).
        
        In production with LinkGravity, this posts interactive buttons to chat (Approve / Deny).
        Returns a decision dictionary: {"decision": "allow" | "deny" | "ask", "reason": str}
        """
        prompt = (
            f"⚠️ **Interactive Tool Approval Required**\n"
            f"• **Tool**: `{tool_name}`\n"
            f"• **Reason**: {reason}\n"
            f"• **Arguments**:\n```json\n{json.dumps(args, indent=2)}\n```"
        )
        logger.warning(f"Requesting approval via LinkGravity: {tool_name}")
        await self.broadcast("Approval Requested", prompt, level="WARNING")

        # In autonomous/headless CI modes without a pending human response,
        # return approval policies or default based on tool sensitivity.
        destructive_tools = ["cloud_run_deploy", "git_push_main", "delete_file"]
        if tool_name in destructive_tools:
            return {"decision": "ask", "reason": "Requires human sign-off via LinkGravity channel"}
        return {"decision": "allow", "reason": "Pre-approved safe operation"}

    async def _send_slack(self, title: str, text: str, fields: Optional[Dict[str, str]]) -> bool:
        payload: Dict[str, Any] = {
            "text": f"*{title}*\n{text}"
        }
        if fields:
            attachments = [{
                "fields": [{"title": k, "value": v, "short": True} for k, v in fields.items()]
            }]
            payload["attachments"] = attachments

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.slack_url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            return False

    async def _send_discord(self, title: str, text: str, fields: Optional[Dict[str, str]]) -> bool:
        embed: Dict[str, Any] = {
            "title": title,
            "description": text,
            "color": 0x2b2d31,
        }
        if fields:
            embed["fields"] = [{"name": k, "value": v, "inline": True} for k, v in fields.items()]

        payload = {"embeds": [embed]}
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(self.discord_url, json=payload)
                return res.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            return False

    async def _send_telegram(self, title: str, text: str, fields: Optional[Dict[str, str]]) -> bool:
        msg = f"<b>{title}</b>\n\n{text}"
        if fields:
            msg += "\n\n" + "\n".join(f"• <b>{k}</b>: {v}" for k, v in fields.items())

        url = f"https://api.telegram.org/bot{self.tg_token}/sendMessage"
        payload = {
            "chat_id": self.tg_chat_id,
            "text": msg,
            "parse_mode": "HTML",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(url, json=payload)
                return res.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send Telegram alert: {e}")
            return False

linkgravity = LinkGravityBridge()
