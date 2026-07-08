import json
import os

import anthropic

from db.connection import get_connection, release_connection

MODEL = 'claude-haiku-4-5-20251001'
BODY_PREVIEW_CHARS = 2000

SYSTEM_PROMPT = """You are a health insurance industry analyst assistant.
Your job is to screen news articles for a senior analyst who tracks major relationship changes
between health insurance carriers and healthcare providers.

Relationship changes of interest include:
- Acquisitions or mergers (insurer buys insurer, provider buys provider, insurer buys provider)
- Partnerships or new network agreements
- Divestitures or spin-offs
- Contract terminations or network exits (a provider leaving an insurer's network, or vice versa)
- TPA or administrator switches (a large employer changing its claims processor)

When in doubt, FLAG IT. We prefer false positives over false negatives — the analyst can quickly
rule out borderline cases, but missed hits can't be recovered.

Do NOT flag: earnings reports with no relationship change, general policy/regulatory news,
clinical/medical research, personnel announcements (unless the role change signals a deal),
or soft PR stories without a concrete business action.

Respond in JSON with exactly two fields:
  "flag": one of "yes", "uncertain", or "no"
  "summary": a 2-sentence plain-English summary of what the article is about
"""


def run_triage(article_ids: list[int], run_id: int) -> list[int]:
    """Triage articles with Claude Haiku and write results to triage_results.

    Returns the subset of article_ids flagged 'yes' or 'uncertain' for the summarizer.
    """
    if not article_ids:
        return []

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    conn = get_connection()
    try:
        flagged_ids = []
        for article_id in article_ids:
            article = _fetch_article(conn, article_id)
            if not article:
                continue
            flag, summary = _call_haiku(client, article)
            _insert_triage_result(conn, article_id, run_id, flag, summary)
            if flag in ('yes', 'uncertain'):
                flagged_ids.append(article_id)
            label = '✓' if flag == 'yes' else '?' if flag == 'uncertain' else '✗'
            print(f'[triage] {label} {article["title"][:70]}')
        print(f'[triage] {len(article_ids)} triaged, {len(flagged_ids)} flagged.')
        return flagged_ids
    finally:
        release_connection(conn)


def _fetch_article(conn, article_id: int) -> dict | None:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT id, title, body_text FROM articles WHERE id = %s',
            (article_id,),
        )
        row = cur.fetchone()
    if not row:
        return None
    return {'id': row[0], 'title': row[1] or '', 'body_text': row[2] or ''}


def _call_haiku(client: anthropic.Anthropic, article: dict) -> tuple[str, str]:
    body_preview = article['body_text'][:BODY_PREVIEW_CHARS]
    user_content = f"Title: {article['title']}\n\nBody (first {BODY_PREVIEW_CHARS} chars):\n{body_preview}"
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_content}],
        )
        text = msg.content[0].text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        result = json.loads(text)
        flag = result.get('flag', 'uncertain')
        if flag not in ('yes', 'uncertain', 'no'):
            flag = 'uncertain'
        return flag, result.get('summary', '')
    except Exception as exc:
        print(f'[triage] warn: haiku call failed for article {article["id"]}: {exc}')
        return 'uncertain', ''


def _insert_triage_result(conn, article_id: int, run_id: int, flag: str, summary: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO triage_results (article_id, scrape_run_id, flag, summary, model)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (article_id, run_id, flag, summary, MODEL),
        )
    conn.commit()
