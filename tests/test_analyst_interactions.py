"""Tests for the Analyst Discord interactions handler (Lambda A) — AGE-94/95."""
import json

from nacl.signing import SigningKey

from agent.analyst import interactions


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


def _command_event(input_text: str, signing_key: SigningKey):
    body = json.dumps({
        "type": interactions.APPLICATION_COMMAND,
        "token": "test-token",
        "data": {"options": [{"name": "input", "value": input_text}]},
    })
    return _event(body, signing_key)


# --- signature verification ---

def test_tampered_body_is_rejected(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    event = _event(json.dumps({"type": interactions.PING}), sk)
    event["body"] = json.dumps({"type": interactions.APPLICATION_COMMAND})

    resp = interactions.handler(event, None)

    assert resp["statusCode"] == 401


def test_wrong_key_is_rejected(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(SigningKey.generate()))
    body = json.dumps({"type": interactions.PING})

    resp = interactions.handler(_event(body, sk), None)

    assert resp["statusCode"] == 401


# --- ping ---

def test_ping_returns_pong(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    body = json.dumps({"type": interactions.PING})

    resp = interactions.handler(_event(body, sk), None)

    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"type": interactions.PONG}


# --- /analysis command ---

def test_command_returns_deferred(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    monkeypatch.setattr(interactions, "_invoke_engine", lambda p: None)

    resp = interactions.handler(_command_event("how does this affect Anthem?", sk), None)

    assert resp["statusCode"] == 200
    assert json.loads(resp["body"]) == {"type": interactions.DEFERRED_CHANNEL_MESSAGE_WITH_SOURCE}


def test_new_analysis_routing(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    captured = {}
    monkeypatch.setattr(interactions, "_invoke_engine", lambda p: captured.update(p))

    interactions.handler(_command_event("https://example.com impact on Anthem?", sk), None)

    assert "conversation_id" not in captured
    assert captured["input_text"] == "https://example.com impact on Anthem?"
    assert captured["mode"] == "engine"
    assert captured["interaction_token"] == "test-token"


def test_continuation_routing(monkeypatch):
    sk = SigningKey.generate()
    monkeypatch.setenv("DISCORD_PUBLIC_KEY", _public_key_hex(sk))
    captured = {}
    monkeypatch.setattr(interactions, "_invoke_engine", lambda p: captured.update(p))

    interactions.handler(_command_event("42 what about the MA book?", sk), None)

    assert captured["conversation_id"] == 42
    assert captured["input_text"] == "what about the MA book?"
    assert captured["mode"] == "engine"
