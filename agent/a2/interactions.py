"""A2 Discord interactions handler — walking skeleton (AGE-94).

Lambda Function URL entry point. Verifies Discord's Ed25519 signature, answers
the verification PING, and returns a stub message for the /analysis command.

The real analysis engine (Claude loop, Neon, deferred response) lands in later
phases. This file only proves the Discord -> AWS -> response pipe.
"""
import base64
import json
import logging
import os

from nacl.exceptions import BadSignatureError
from nacl.signing import VerifyKey

log = logging.getLogger()
log.setLevel(logging.INFO)

# Discord interaction + response type codes
PING = 1
APPLICATION_COMMAND = 2
PONG = 1
CHANNEL_MESSAGE_WITH_SOURCE = 4


def _verify_signature(public_key: str, signature: str, timestamp: str, body: str) -> bool:
    """Return True if the Ed25519 signature matches the raw request body."""
    try:
        VerifyKey(bytes.fromhex(public_key)).verify(
            f"{timestamp}{body}".encode(), bytes.fromhex(signature)
        )
        return True
    except (BadSignatureError, ValueError):
        return False


def _raw_body(event: dict) -> str:
    """Extract the raw request body from a Lambda Function URL event."""
    body = event.get("body") or ""
    if event.get("isBase64Encoded"):
        body = base64.b64decode(body).decode()
    return body


def _response(status: int, payload: dict | None = None) -> dict:
    return {
        "statusCode": status,
        "headers": {"content-type": "application/json"},
        "body": json.dumps(payload) if payload is not None else "",
    }


def handler(event, context):
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    signature = headers.get("x-signature-ed25519", "")
    timestamp = headers.get("x-signature-timestamp", "")
    body = _raw_body(event)

    if not _verify_signature(os.environ["DISCORD_PUBLIC_KEY"], signature, timestamp, body):
        return _response(401, {"error": "invalid request signature"})

    interaction = json.loads(body)

    if interaction.get("type") == PING:
        return _response(200, {"type": PONG})

    if interaction.get("type") == APPLICATION_COMMAND:
        return _response(200, {
            "type": CHANNEL_MESSAGE_WITH_SOURCE,
            "data": {"content": "🟢 A2 stub is alive — analysis engine coming soon."},
        })

    return _response(200, {"type": PONG})
