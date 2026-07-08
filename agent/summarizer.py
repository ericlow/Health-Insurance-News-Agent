import json
import os

import anthropic

from db.connection import get_connection, release_connection

MODEL = 'claude-sonnet-4-6'

SYSTEM_PROMPT = """You are a briefing tool for a health insurance industry analyst.
You receive a news article about a potential relationship change between a health insurance carrier
and a healthcare provider. Your job is to extract a concise, structured summary.

Be specific and factual. Use entity names, not pronouns. If a field cannot be determined from
the article, write "Not stated" — do not infer or speculate.

Respond in JSON with exactly four fields:
  "what_happened": 2–3 sentences describing the specific business action or change
  "who": the key entities and their roles (e.g. "Northwell Health (provider) · Fidelis Care / Centene (insurer)")
  "impact": members affected, revenue at stake, or market scope — use numbers from the article if available
  "why_it_matters": 1–2 sentences on the strategic significance or precedent this sets
"""


def run_summarizer(article_ids: list[int], run_id: int) -> list[int]:
    """Summarize flagged articles with Claude Sonnet and write results to briefings.

    Returns the list of briefing IDs created.
    """
    if not article_ids:
        return []

    client = anthropic.Anthropic(api_key=os.environ['ANTHROPIC_API_KEY'])
    conn = get_connection()
    try:
        briefing_ids = []
        for article_id in article_ids:
            article = _fetch_article(conn, article_id)
            if not article:
                continue
            triage_result_id = _fetch_triage_result_id(conn, article_id)
            if not triage_result_id:
                continue
            brief = _call_sonnet(client, article)
            briefing_id = _insert_briefing(conn, article_id, triage_result_id, run_id, brief)
            briefing_ids.append(briefing_id)
            print(f'[summarizer] briefed: {article["title"][:70]}')
        print(f'[summarizer] {len(article_ids)} articles → {len(briefing_ids)} briefings.')
        return briefing_ids
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


def _fetch_triage_result_id(conn, article_id: int) -> int | None:
    with conn.cursor() as cur:
        cur.execute(
            'SELECT id FROM triage_results WHERE article_id = %s ORDER BY triaged_at DESC LIMIT 1',
            (article_id,),
        )
        row = cur.fetchone()
    return row[0] if row else None


def _call_sonnet(client: anthropic.Anthropic, article: dict) -> dict:
    user_content = f"Title: {article['title']}\n\nFull article:\n{article['body_text']}"
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_content}],
        )
        text = msg.content[0].text.strip()
        if text.startswith('```'):
            text = text.split('```')[1]
            if text.startswith('json'):
                text = text[4:]
        result = json.loads(text)
        return {
            'what_happened': result.get('what_happened', 'Not stated'),
            'who': result.get('who', 'Not stated'),
            'impact': result.get('impact', 'Not stated'),
            'why_it_matters': result.get('why_it_matters', 'Not stated'),
        }
    except Exception as exc:
        print(f'[summarizer] warn: sonnet call failed for article {article["id"]}: {exc}')
        return {
            'what_happened': 'Not stated',
            'who': 'Not stated',
            'impact': 'Not stated',
            'why_it_matters': 'Not stated',
        }


def _insert_briefing(conn, article_id: int, triage_result_id: int, run_id: int, brief: dict) -> int:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO briefings
                (article_id, triage_result_id, scrape_run_id,
                 what_happened, who, impact, why_it_matters, model)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (article_id, triage_result_id, run_id,
             brief['what_happened'], brief['who'], brief['impact'],
             brief['why_it_matters'], MODEL),
        )
        briefing_id = cur.fetchone()[0]
    conn.commit()
    return briefing_id
