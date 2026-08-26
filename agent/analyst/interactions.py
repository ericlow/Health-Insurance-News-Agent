"""Analyst Discord interactions handler — Lambda A (AGE-94/95).

Verifies Discord's Ed25519 signature, answers the verification PING, and
for /analysis commands: returns a deferred response (type 5, thinking spinner)
then asynchronously invokes the engine (engine mode of the same Lambda) to run
the Claude loop and post results back to Discord.

Engine mode: when the Lambda is invoked with {"mode": "engine", ...}, this
handler delegates to agent.analyst.engine.handler. This lets a single Lambda
function serve both roles, avoiding a second function and its infra.
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
DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE = 5


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


def _invoke_engine(payload: dict):
    import boto3  # lazy — pre-installed in Lambda runtime; mock in tests via monkeypatch
    region = os.environ.get("AWS_REGION", "us-west-1")
    fn = os.environ.get("AWS_LAMBDA_FUNCTION_NAME", "analyst-handler")
    boto3.client("lambda", region_name=region).invoke(
        FunctionName=fn,
        InvocationType="Event",
        Payload=json.dumps(payload).encode(),
    )


def handler(event, context):
    # Engine mode: async self-invocation from Lambda A
    if event.get("mode") == "engine":
        from agent.analyst import engine
        return engine.handler(event, context)

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
        options = (interaction.get("data") or {}).get("options") or []
        input_text = next((o["value"] for o in options if o["name"] == "input"), "")
        token = interaction.get("token", "")

        parts = input_text.split()
        if parts and parts[0].isdigit():
            payload = {
                "mode": "engine",
                "interaction_token": token,
                "input_text": " ".join(parts[1:]),
                "conversation_id": int(parts[0]),
            }
        else:
            payload = {
                "mode": "engine",
                "interaction_token": token,
                "input_text": input_text,
            }

        _invoke_engine(payload)
        return _response(200, {"type": DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE})

    return _response(200, {"type": PONG})
