"""Discord I/O — parse incoming Lambda events and send responses back to Discord."""
import logging
import os

import requests

log = logging.getLogger()

DISCORD_API = "https://discord.com/api/v10"


def parse_discord(event: dict) -> tuple[str, str, int | None]:
    """Extract Discord interaction fields from the raw Lambda event payload."""
    return event["interaction_token"], event["input_text"], event.get("conversation_id")


def patch_status(token: str, text: str):
    """Post a status update as a new followup message so history is preserved."""
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    try:
        requests.post(
            f"{DISCORD_API}/webhooks/{app_id}/{token}",
            json={"content": text},
            timeout=10,
        )
    except Exception:
        log.exception("Failed to post Discord status")


def send_discord(token: str, content: str):
    """Send content back to Discord, patching the deferred reply and posting overflow chunks."""
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    chunks = split(content)
    base = f"{DISCORD_API}/webhooks/{app_id}/{token}"
    try:
        requests.patch(f"{base}/messages/@original", json={"content": chunks[0]}, timeout=10)
        for chunk in chunks[1:]:
            requests.post(base, json={"content": chunk}, timeout=10)
    except Exception:
        log.exception("Failed to send Discord response")


def split(text: str, limit: int = 2000) -> list[str]:
    """Split a long string into Discord-safe chunks (max 2000 chars each)."""
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]
