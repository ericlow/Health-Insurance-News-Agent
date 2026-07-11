import json
import os

import anthropic

from db.connection import get_connection, release_connection

MODEL = 'claude-haiku-4-5-20251001'
BODY_PREVIEW_CHARS = 2000
# Triage response is a small JSON object — well under 200 tokens in practice.
# 512 provides headroom for the reason field without risking truncation.
MAX_TOKENS = 512

TITLE_SYSTEM_PROMPT = """You are a health insurance industry analyst assistant.
Your job is to screen news articles for a senior analyst who tracks major relationship changes
between health insurance carriers and healthcare providers.  The team is responsible for these target states: CA, NV, CO, MO, WI, NY and NJ.

There are two major classes of interest. Nation wide changes which has state level impact, and state level changes.

At the national level, we are concerned with changes that could affect the states.  In these articles the states might not be named directly.
1. ACA related
2. universal healthcare, MFA, single payor
3. the federal level increasing or decreasing responsibility with the state level.

At the state level, we are concerned with the target states.
Relationship changes of interest include:
4. Acquisitions or mergers (insurer buys insurer, provider buys provider, insurer buys provider)
5. Partnerships or new network agreements
6. Divestitures or spin-offs
7. Contract terminations or network exits (a provider leaving an insurer's network, or vice versa)
8. TPA or administrator switches (a large employer changing its claims processor)
9. if it includes Cigna vs UC Health in target states, immediately flag
10. anything related to universal healthcare in CA
11. mandated mental health benefits
12. federal responsibilities and funding being shifted to the state level

General Topics of interest at the state level:
13. glp-1, a major cost driver
14. ACA related
15. universal healthcare, MFA, single payor
16. labor unions

When in doubt, FLAG IT. We prefer false positives over false negatives — the analyst can quickly rule out borderline cases, but missed hits can't be recovered.

Do NOT flag:
A. earnings reports with no relationship change
B. general policy/regulatory news
C. clinical/medical research
D. personnel announcements (unless the role change signals a deal)
E. soft PR stories without a concrete business action.

Respond in JSON with exactly 4 fields:
  "flag": one of "yes", "uncertain", or "no"
  "confidence": 1-5 score. 5 being most confident. 1 least.
  "scope": "national" or state abbreviation. ex: "CA"
  "reason": number of the item 1-16 above. ex: "9. if it includes Cigna vs UC Health in target states, immediately flag"
"""

ARTICLE_SYSTEM_PROMPT = """You are a health insurance industry analyst assistant.
Your job is to screen news articles for a senior analyst who tracks major relationship changes
between health insurance carriers and healthcare providers.  The team is responsible for these target states: CA, NV, CO, MO, WI, NY and NJ.

There are two major classes of interest. Nation wide changes which has state level impact, and state level changes.

At the national level, we are concerned with changes that could affect the states.  In these articles the states might not be named directly.
1. ACA related
2. universal healthcare, MFA, single payor
3. the federal level increasing or decreasing responsibility with the state level.

At the state level, we are concerned with the target states.
Relationship changes of interest include:
4. Acquisitions or mergers (insurer buys insurer, provider buys provider, insurer buys provider)
5. Partnerships or new network agreements
6. Divestitures or spin-offs
7. Contract terminations or network exits (a provider leaving an insurer's network, or vice versa)
8. TPA or administrator switches (a large employer changing its claims processor)
9. if it includes Cigna vs UC Health in target states, immediately flag
10. anything related to universal healthcare in CA
11. mandated mental health benefits
12. federal responsibilities and funding being shifted to the state level

General Topics of interest at the state level:
13. glp-1, a major cost driver
14. ACA related
15. universal healthcare, MFA, single payor
16. labor unions

When in doubt, FLAG IT. We prefer false positives over false negatives — the analyst can quickly
rule out borderline cases, but missed hits can't be recovered.

Do NOT flag:
A. earnings reports with no relationship change
B. general policy/regulatory news
C. clinical/medical research
D. personnel announcements (unless the role change signals a deal)
E. soft PR stories without a concrete business action.

Respond in JSON with exactly 5 fields:
  "flag": one of "yes", "uncertain", or "no"
  "confidence": 1-5 score. 5 being most confident. 1 least.
  "summary": a 2-sentence plain-English summary of what the article is about
  "scope": "national" or state abbreviation. ex: "CA"
  "reason": number of the item 1-16 above. ex: "9. if it includes Cigna vs UC Health in target states, immediately flag"
"""


def run_triage(article_ids: list[int], run_id: int) -> list[int]:
    """Two-stage triage: title filter first, full article eval for survivors.

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

            title_flag, title_confidence, title_scope, title_reason = _call_haiku_title(client, article)
            if title_flag == 'no':
                print(f'[triage] ✗ (title) {article["title"][:70]}')
                _insert_triage_result(
                    conn, article_id, run_id,
                    title_flag, title_confidence, title_scope, title_reason,
                    None, None, None, None, None,
                )
                continue

            article_flag, article_confidence, article_summary, article_scope, article_reason = \
                _call_haiku_article(client, article)
            _insert_triage_result(
                conn, article_id, run_id,
                title_flag, title_confidence, title_scope, title_reason,
                article_flag, article_confidence, article_summary, article_scope, article_reason,
            )
            if article_flag in ('yes', 'uncertain'):
                flagged_ids.append(article_id)
            label = '✓' if article_flag == 'yes' else '?' if article_flag == 'uncertain' else '✗'
            print(f'[triage] {label} [{article_scope}] {article["title"][:70]}')

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


def _call_haiku_title(client: anthropic.Anthropic, article: dict) -> tuple[str, int, str, str]:
    """Screen the article title only. Returns (flag, confidence, scope, reason)."""
    user_content = f"Title: {article['title']}"
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=TITLE_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_content}],
        )
        result = _parse_response(msg.content[0].text)
        flag = result.get('flag', 'uncertain')
        if flag not in ('yes', 'uncertain', 'no'):
            flag = 'uncertain'
        return flag, result.get('confidence', 3), result.get('scope', ''), result.get('reason', '')
    except Exception as exc:
        print(f'[triage] warn: title call failed for article {article["id"]}: {exc}')
        return 'uncertain', 3, '', ''


def _call_haiku_article(client: anthropic.Anthropic, article: dict) -> tuple[str, int, str, str, str]:
    """Evaluate the full article. Returns (flag, confidence, summary, scope, reason)."""
    body_preview = article['body_text'][:BODY_PREVIEW_CHARS]
    user_content = f"Title: {article['title']}\n\nBody (first {BODY_PREVIEW_CHARS} chars):\n{body_preview}"
    try:
        msg = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ARTICLE_SYSTEM_PROMPT,
            messages=[{'role': 'user', 'content': user_content}],
        )
        result = _parse_response(msg.content[0].text)
        flag = result.get('flag', 'uncertain')
        if flag not in ('yes', 'uncertain', 'no'):
            flag = 'uncertain'
        return flag, result.get('confidence', 3), result.get('summary', ''), result.get('scope', ''), result.get('reason', '')
    except Exception as exc:
        print(f'[triage] warn: article call failed for article {article["id"]}: {exc}')
        return 'uncertain', 3, '', '', ''


def _parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
    return json.loads(text)


def _insert_triage_result(
    conn,
    article_id: int,
    run_id: int,
    title_flag: str,
    title_confidence: int,
    title_scope: str,
    title_reason: str,
    article_flag: str | None,
    article_confidence: int | None,
    article_summary: str | None,
    article_scope: str | None,
    article_reason: str | None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO triage_results (
                article_id, scrape_run_id,
                title_flag, title_confidence, title_scope, title_reason,
                article_flag, article_confidence, article_summary, article_scope, article_reason,
                model
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                article_id, run_id,
                title_flag, title_confidence, title_scope, title_reason,
                article_flag, article_confidence, article_summary, article_scope, article_reason,
                MODEL,
            ),
        )
    conn.commit()
