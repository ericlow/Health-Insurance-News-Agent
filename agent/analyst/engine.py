"""AnalystAgent engine — Lambda B (AGE-95).

Runs the Claude tool-use loop, persists conversation state to Neon,
and sends the analysis back to Discord.

Invoked asynchronously by Lambda A (interactions.handler) with:
  {"mode": "engine", "interaction_token": "...", "input_text": "...",
   "conversation_id": <int>}   # conversation_id absent for new analyses
"""
import json
import logging
import re

import anthropic

from agent.analyst import persistence
from agent.analyst.discord import delete_original, parse_discord, post_channel_message, send_discord, split
from agent.analyst.tools import fetch_url, lookup_regulatory_rules, search_web

log = logging.getLogger()
log.setLevel(logging.INFO)

MAX_TOOL_CALLS = 20
MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = """You are an expert health insurance industry analyst at Elevance Health \
(Anthem Blue Cross CA). Analyze market events for their impact on Elevance's competitive \
position, membership, networks, and financials.

Start every analysis by calling lookup_regulatory_rules. Read every mechanism it returns \
and consider whether it applies before doing anything else. Then use search_web to locate \
relevant sources and fetch_url to read primary data. Before drawing conclusions, read at \
least 3 URLs with fetch_url.

Tag regulatory mechanism claims as [MECHANISM] — established program rule verifiable in \
statute or regulation, not requiring a source URL.

Write the final analysis in this exact structure:

1. A single bold verdict line — risk level and one-sentence strategic read. Example: \
"**Low immediate risk. Strategically notable. Watch CA/AZ county filings.**"

2. 3–5 findings. Each starts with a bold label word ("**Distribution:**", "**Geography:**", \
"**Timing:**"), followed by 1–2 sentences. No headers, no bullets beyond the label.

3. A "**Bottom line:**" line — one sentence, phrased as a directive (what Elevance should do).

4. A "**Ask me about:**" line — follow-up topics as a short inline list separated by · dots.

No inline citations. No confidence tags. No section headers. Keep the total under 250 words."""

TOOLS = [
    {
        "name": "lookup_regulatory_rules",
        "description": (
            "Read the standing regulatory mechanisms that govern member flows "
            "across CA, NV, CO, MO, WI, NY, and NJ. Call this first, before "
            "any web search or data fetch. Returns the full rules document."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
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
    "lookup_regulatory_rules": lambda inp: lookup_regulatory_rules(),
    "fetch_url": lambda inp: fetch_url(inp["url"]),
    "search_web": lambda inp: search_web(inp["query"]),
}


def _search_result_summary(result_str: str) -> str:
    try:
        results = json.loads(result_str)
        if not isinstance(results, list):
            return ""
        lines = []
        for r in results[:5]:
            line = f"- [{r.get('title', r.get('url', ''))}]({r.get('url', '')})"
            meta = " — ".join(filter(None, [r.get("date", ""), r.get("snippet", "")]))
            if meta:
                line += f"\n  {meta}"
            lines.append(line)
        return "\n".join(lines)
    except (json.JSONDecodeError, AttributeError):
        return ""


def _cite(analysis: str, fetched_urls: list[str]) -> str:
    """Add inline citation numbers to the analysis and append a sources footer."""
    if not fetched_urls:
        return analysis
    numbered = "\n".join(f"({i + 1}) {url}" for i, url in enumerate(fetched_urls))
    resp = anthropic.Anthropic().messages.create(
        model=MODEL,
        max_tokens=2048,
        messages=[{"role": "user", "content": (
            "Add inline citation numbers to this analysis using the numbered sources below. "
            "Insert (1), (2), etc. immediately after the claim each source supports. "
            "Only cite sources that directly support a specific claim. "
            "Return only the annotated analysis text, unchanged except for added citation numbers.\n\n"
            f"Analysis:\n{analysis}\n\nSources:\n{numbered}"
        )}],
    )
    annotated = resp.content[0].text.strip()
    used = sorted({int(m) for m in re.findall(r'\((\d+)\)', annotated) if 1 <= int(m) <= len(fetched_urls)})
    if not used:
        return analysis
    footer = "\n\n**Sources**\n" + "\n".join(f"({n}) <{fetched_urls[n - 1]}>" for n in used)
    return annotated + footer


def _run_loop(messages: list, token: str, channel_id: str) -> str:
    """Run the Claude tool-use loop until Claude produces a final text response or hits the tool call limit."""
    client = anthropic.Anthropic()
    total_tool_calls = 0
    fetched_urls: list[str] = []

    while True:
        at_limit = total_tool_calls >= MAX_TOOL_CALLS
        if at_limit:
            post_channel_message(channel_id, f"Reached research limit ({MAX_TOOL_CALLS} tool calls). Writing analysis...")
        kwargs = {"tools": TOOLS} if not at_limit else {}
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
            text = next((b["text"] for b in content_blocks if b.get("type") == "text"), "")
            return _cite(text, fetched_urls)

        # Post any reasoning text Claude emitted alongside the tool calls.
        for block in content_blocks:
            if block.get("type") == "text" and block.get("text", "").strip():
                post_channel_message(channel_id, block["text"].strip())

        tool_results = []
        for block in resp.content:
            if block.type == "tool_use":
                total_tool_calls += 1
                if block.name == "search_web":
                    status = f'Searching: "{block.input.get("query", "")}"'
                elif block.name == "fetch_url":
                    url = block.input.get("url", "")
                    fetched_urls.append(url)
                    status = f"Reading: {url}"
                else:
                    status = f"Running: {block.name}"
                log.info("[B] tool call %d: %s", total_tool_calls, status)
                post_channel_message(channel_id, status)

                result = _TOOL_DISPATCH[block.name](block.input)
                result_str = result if isinstance(result, str) else json.dumps(result)
                log.info("[B] tool result len=%d", len(result_str))

                if block.name == "search_web":
                    summary = _search_result_summary(result_str)
                    if summary:
                        post_channel_message(channel_id, f"Found:\n{summary}")
                elif block.name == "fetch_url":
                    post_channel_message(channel_id, f"Retrieved {len(result_str):,} chars")

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result_str,
                })
        messages.append({"role": "user", "content": tool_results})


def handler(event, context):
    """Lambda B entry point: load or create a conversation, run the tool loop, and send the result to Discord."""
    token, input_text, conversation_id, channel_id = parse_discord(event)

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
        post_channel_message(channel_id, f"**Analyzing:** {input_text}")
        analysis = _run_loop(messages, token, channel_id)
        log.info("[B] analysis complete len=%d", len(analysis))
        persistence.update_conversation(db, conversation_id, messages)
        delete_original(token)
        for chunk in split(f"{analysis}\n\nConversation ID: {conversation_id}"):
            post_channel_message(channel_id, chunk)
    except Exception as e:
        log.exception("Engine failed: %s", e)
        send_discord(token, f"Analysis failed: {e}")
    finally:
        if db:
            db.close()
