"""AnalystAgent engine — Lambda B (AGE-95).

Runs the Claude tool-use loop, persists conversation state to Neon,
and patches the Discord deferred response with the analysis.

Invoked asynchronously by Lambda A (interactions.handler) with:
  {"mode": "engine", "interaction_token": "...", "input_text": "...",
   "conversation_id": <int>}   # conversation_id absent for new analyses
"""
import json
import logging
import os

import anthropic
import psycopg2
import requests
from bs4 import BeautifulSoup
from psycopg2.extras import Json

from agent import http_utils

log = logging.getLogger()
log.setLevel(logging.INFO)

DISCORD_API = "https://discord.com/api/v10"
MAX_TOOL_CALLS = 10
MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are an expert health insurance industry analyst at Elevance Health \
(Anthem Blue Cross CA). Analyze market events for their impact on Elevance's competitive \
position, membership, networks, and financials.

Tag every factual claim with a confidence level:
[HIGH] — directly stated in a fetched primary source
[MED] — inferred from secondary sources or industry context
[LOW] — analyst estimate or projection

Focus on: network impacts, membership effects, competitive dynamics, regulatory implications. \
Be direct and specific. Use fetch_url to retrieve article text before analyzing."""

TOOLS = [
    {
        "name": "fetch_url",
        "description": "Fetch the readable text of a web page for analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"},
            },
            "required": ["url"],
        },
    }
]


def _fetch_url(url: str) -> str:
    try:
        resp = http_utils.get(url, timeout=30)
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "nav", "footer"]):
            tag.decompose()
        # ponytail: cap at 50k chars to stay in context window; raise if pages routinely exceed this
        return soup.get_text(separator="\n", strip=True)[:50000]
    except Exception as e:
        return json.dumps({"error": str(e)})


def _split(text: str, limit: int = 2000) -> list[str]:
    if len(text) <= limit:
        return [text]
    return [text[i : i + limit] for i in range(0, len(text), limit)]


def _patch_discord(token: str, content: str):
    app_id = os.environ["DISCORD_APPLICATION_ID"]
    chunks = _split(content)
    base = f"{DISCORD_API}/webhooks/{app_id}/{token}"
    try:
        requests.patch(f"{base}/messages/@original", json={"content": chunks[0]}, timeout=10)
        for chunk in chunks[1:]:
            requests.post(base, json={"content": chunk}, timeout=10)
    except Exception:
        log.exception("Failed to patch Discord response")


def _conn():
    return psycopg2.connect(os.environ["DATABASE_URL"])


def _create_conversation(conn, messages: list) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO a2_conversations (messages) VALUES (%s) RETURNING id",
            (Json(messages),),
        )
        row = cur.fetchone()
    conn.commit()
    return row[0]


def _load_conversation(conn, conv_id: int) -> list | None:
    with conn.cursor() as cur:
        cur.execute("SELECT messages FROM a2_conversations WHERE id = %s", (conv_id,))
        row = cur.fetchone()
    if not row:
        return None
    raw = row[0]
    return raw if isinstance(raw, list) else json.loads(raw)


def _update_conversation(conn, conv_id: int, messages: list):
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE a2_conversations SET messages = %s, updated_at = now() WHERE id = %s",
            (Json(messages), conv_id),
        )
    conn.commit()


def _run_loop(messages: list) -> str:
    client = anthropic.Anthropic()
    total_tool_calls = 0

    while True:
        kwargs = {"tools": TOOLS} if total_tool_calls < MAX_TOOL_CALLS else {}
        resp = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=messages,
            **kwargs,
        )

        content_blocks = [b.model_dump() for b in resp.content]
        messages.append({"role": "assistant", "content": content_blocks})

        if resp.stop_reason != "tool_use":
            return next((b["text"] for b in content_blocks if b.get("type") == "text"), "")

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                total_tool_calls += 1
                result = _fetch_url(block.input["url"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })
        messages.append({"role": "user", "content": tool_results})


def handler(event, context):
    token = event["interaction_token"]
    input_text = event["input_text"]
    conversation_id = event.get("conversation_id")

    conn = _conn()
    try:
        if conversation_id is not None:
            messages = _load_conversation(conn, conversation_id)
            if messages is None:
                _patch_discord(token, f"No conversation found with ID {conversation_id}")
                return
            messages.append({"role": "user", "content": input_text})
        else:
            messages = [{"role": "user", "content": input_text}]
            conversation_id = _create_conversation(conn, messages)

        analysis = _run_loop(messages)
        _update_conversation(conn, conversation_id, messages)
        _patch_discord(token, f"{analysis}\n\nConversation ID: {conversation_id}")
    except Exception as e:
        log.exception("Engine failed")
        _patch_discord(token, f"Analysis failed: {e}")
    finally:
        conn.close()
