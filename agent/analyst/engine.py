"""AnalystAgent engine — Lambda B (AGE-95).

Runs the Claude tool-use loop, persists conversation state to Neon,
and sends the analysis back to Discord.

Invoked asynchronously by Lambda A (interactions.handler) with:
  {"mode": "engine", "interaction_token": "...", "input_text": "...",
   "conversation_id": <int>}   # conversation_id absent for new analyses
"""
import json
import logging
from urllib.parse import urlparse

import anthropic

from agent.analyst import persistence
from agent.analyst.discord import parse_discord, patch_status, send_discord
from agent.analyst.tools import fetch_url, search_web

log = logging.getLogger()
log.setLevel(logging.INFO)

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
Be direct and specific. Start every analysis with search_web to locate relevant sources. \
Before drawing conclusions, read at least 3 URLs with fetch_url. \
Cite the source URL for each factual claim."""

TOOLS = [
    {
        "name": "fetch_url",
        "description": "Fetch the readable text of a web page for analysis.",
        "input_schema": {
            "type": "object",
            "properties": {"url": {"type": "string", "description": "The URL to fetch"}},
            "required": ["url"],
        },
    },
    {
        "name": "search_web",
        "description": "Search the web and return top results with titles, URLs, and snippets.",
        "input_schema": {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "The search query"}},
            "required": ["query"],
        },
    },
]

_TOOL_DISPATCH = {
    "fetch_url": lambda inp: fetch_url(inp["url"]),
    "search_web": lambda inp: search_web(inp["query"]),
}


def _status_text(tool_name: str, tool_input: dict) -> str:
    if tool_name == "search_web":
        return f'Searching: "{tool_input.get("query", "")}"'
    if tool_name == "fetch_url":
        url = tool_input.get("url", "")
        return f"Reading: {urlparse(url).netloc or url}"
    return f"Running: {tool_name}"


def _run_loop(messages: list, token: str) -> str:
    """Run the Claude tool-use loop until Claude produces a final text response or hits the tool call limit."""
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
                status = _status_text(block.name, block.input)
                log.info("[B] tool call %d: %s", total_tool_calls, status)
                patch_status(token, status)
                result = _TOOL_DISPATCH[block.name](block.input)
                result_str = result if isinstance(result, str) else json.dumps(result)
                log.info("[B] tool result len=%d", len(result_str))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
        messages.append({"role": "user", "content": tool_results})


def handler(event, context):
    """Lambda B entry point: load or create a conversation, run the tool loop, and send the result to Discord."""
    token, input_text, conversation_id = parse_discord(event)

    db = None
    try:
        db = persistence.conn()
        if conversation_id is not None:
            messages = persistence.load_conversation(db, conversation_id)
            if messages is None:
                send_discord(token, f"No conversation found with ID {conversation_id}")
                return
            messages.append({"role": "user", "content": input_text})
        else:
            messages = [{"role": "user", "content": input_text}]
            conversation_id = persistence.create_conversation(db, messages)

        log.info("[B] start: cid=%s input=%r", conversation_id, input_text[:80])
        analysis = _run_loop(messages, token)
        log.info("[B] analysis complete len=%d", len(analysis))
        persistence.update_conversation(db, conversation_id, messages)
        send_discord(token, f"{analysis}\n\nConversation ID: {conversation_id}")
    except Exception as e:
        log.exception("Engine failed: %s", e)
        send_discord(token, f"Analysis failed: {e}")
    finally:
        if db:
            db.close()
