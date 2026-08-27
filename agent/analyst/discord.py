"""Discord I/O — parse incoming Lambda events and send responses back to Discord."""
import logging
import os

import requests

log = logging.getLogger()

DISCORD_API = "https://discord.com/api/v10"


def parse_discord(event: dict) -> tuple[str, str, int | None, str]:
    """Extract Discord interaction fields from the raw Lambda event payload."""
    return (
        event["interaction_token"],
        event["input_text"],
        event.get("conversation_id"),
        event.get("channel_id", ""),
    )


def post_channel_message(channel_id: str, text: str) -> str | None:
    """Post a message directly to a Discord channel using the bot token. Returns the message snowflake ID or None."""
    try:
        resp = requests.post(
            f"{DISCORD_API}/channels/{channel_id}/messages",
            headers={"Authorization": f"Bot {os.environ['DISCORD_BOT_TOKEN']}"},
            json={"content": text, "flags": 4},
            timeout=10,
        )
        try:
            return resp.json().get("id")
        except Exception:
            return None
    except Exception:
        log.exception("Failed to post channel message")
        return None


def create_thread(channel_id: str, message_id: str, name: str) -> str | None:
    """Create a Discord thread on a specific message. Returns thread_id or None on failure."""
    try:
        resp = requests.post(
            f"{DISCORD_API}/channels/{channel_id}/messages/{message_id}/threads",
            headers={"Authorization": f"Bot {os.environ['DISCORD_BOT_TOKEN']}"},
            json={"name": name[:100], "auto_archive_duration": 1440},
            timeout=10,
        )
        try:
            return resp.json().get("id")
        except Exception:
            return None
    except Exception:
        log.exception("Failed to create thread")
        return None


def delete_original(token: str):
    """Delete the deferred @original placeholder message."""
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    try:
        requests.delete(
            f"{DISCORD_API}/webhooks/{app_id}/{token}/messages/@original",
            timeout=10,
        )
    except Exception:
        log.exception("Failed to delete original message")


def send_discord(token: str, content: str):
    """Send content back to Discord, patching the deferred reply and posting overflow chunks."""
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    chunks = split(content)
    base = f"{DISCORD_API}/webhooks/{app_id}/{token}"
    try:
        requests.patch(f"{base}/messages/@original", json={"content": chunks[0], "flags": 4}, timeout=10)
        for chunk in chunks[1:]:
            requests.post(base, json={"content": chunk, "flags": 4}, timeout=10)
    except Exception:
        log.exception("Failed to send Discord response")


def split(text: str, limit: int = 2000) -> list[str]:
    """Split a long string into Discord-safe chunks (max 2000 chars each)."""
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]
