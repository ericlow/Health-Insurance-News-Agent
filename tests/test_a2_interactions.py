"""Tests for the A2 Discord interactions stub (AGE-94).

Generates a real Ed25519 keypair so signature verification is exercised end to
end without needing Discord's actual public key.
"""
import json

from nacl.signing import SigningKey

from agent.a2 import interactions


def _event(body: str, signing_key: SigningKey, timestamp: str = "1700000000"):
    signature = signing_key.sign(f"{timestamp}{body}".encode()).signature.hex()
    return {
        "headers": {
            "x-signature-ed25519": signature,
            "x-signature-timestamp": timestamp,
        },
        "body": body,
        "isBase64Encoded": False,
    }


def _public_key_hex(signing_key: SigningKey) -> str:
    return signing_key.verify_key.encode().hex()


def test_ping_returns_pong(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    body = json.dumps({"type": interactions.PING})

    resp = interactions.handler(_event(body, sk), None)

    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"type": interactions.PONG}


def test_command_returns_stub_message(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    body = json.dumps({"type": interactions.APPLICATION_COMMAND})

    resp = interactions.handler(_event(body, sk), None)

    payload = json.loads(resp["body"])
    assert payload["type"] == interactions.CHANNEL_MESSAGE_WITH_SOURCE
    assert "stub is alive" in payload["data"]["content"]


def test_tampered_body_is_rejected(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    event = _event(json.dumps({"type": interactions.PING}), sk)
    event["body"] = json.dumps({"type": interactions.APPLICATION_COMMAND})  # signature no longer matches

    resp = interactions.handler(event, None)

    assert resp["statusCode"] == 401


def test_wrong_key_is_rejected(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(SigningKey.generate()))  # different key
    body = json.dumps({"type": interactions.PING})

    resp = interactions.handler(_event(body, sk), None)

    assert resp["statusCode"] == 401
