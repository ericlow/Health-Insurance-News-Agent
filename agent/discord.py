import logging
import os
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests

from db.connection import get_connection, release_connection

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━"
_LA = ZoneInfo("America/Los_Angeles")
_HEALTH_CHECK_MAX_ATTEMPTS = 3


def _fetch_unsent_briefings(conn, verdict: str, run_id=None):
    """Fetch unsent briefings filtered by triage verdict ('yes' or 'uncertain')."""
    cur = conn.cursor()
    base = """
        SELECT b.id, b.what_happened, b.who, b.impact, b.why_it_matters,
               a.title, a.url
        FROM briefings b
        JOIN articles a ON a.id = b.article_id
        JOIN triage_results tr ON tr.id = b.triage_result_id
        WHERE b.discord_sent_at IS NULL
          AND tr.article_flag = %s
    """
    if run_id is not None:
        cur.execute(base + " AND b.scrape_run_id = %s ORDER BY b.created_at", (verdict, run_id))
    else:
        cur.execute(base + " ORDER BY b.created_at", (verdict,))
    rows = cur.fetchall()
    cur.close()
    return rows


def _fetch_unsent_no_articles(conn, run_id=None):
    """Fetch triage_results for 'no' articles not yet sent to the no channel."""
    cur = conn.cursor()
    base = """
        SELECT tr.id, a.title, a.url,
               tr.article_flag,
               tr.title_reason, tr.title_confidence, tr.title_scope,
               tr.article_reason, tr.article_confidence, tr.article_scope, tr.article_summary
        FROM triage_results tr
        JOIN articles a ON a.id = tr.article_id
        WHERE tr.discord_no_sent_at IS NULL
          AND (tr.article_flag = 'no'
               OR (tr.title_flag = 'no' AND tr.article_flag IS NULL))
    """
    if run_id is not None:
        cur.execute(base + " AND tr.scrape_run_id = %s ORDER BY tr.triaged_at", (run_id,))
    else:
        cur.execute(base + " ORDER BY tr.triaged_at")
    rows = cur.fetchall()
    cur.close()
    return rows


def _format_briefing(row):
    _, what_happened, who, impact, why_it_matters, title, url = row
    lines = [
        DIVIDER,
        f"📌 {title}",
        "",
        f"What happened: {what_happened}",
        "",
        f"Who's involved: {who}",
        "",
        f"Members/revenue at stake: {impact}",
        "",
        f"Why it matters: {why_it_matters}",
        "",
        f"🔗 {url}",
        DIVIDER,
    ]
    return "\n".join(lines)


def _format_no_article(title, url, article_flag,
                       title_reason, title_confidence, title_scope,
                       article_reason, article_confidence, article_scope, article_summary):
    title_rejected = article_flag is None
    if title_rejected:
        label = "❌ Title rejected"
        reason = title_reason or ""
        confidence = title_confidence
        scope = title_scope or ""
        summary = None
    else:
        label = "❌ Article rejected"
        reason = article_reason or ""
        confidence = article_confidence
        scope = article_scope or ""
        summary = article_summary

    lines = [f"[{title}]({url})", label]
    if reason:
        lines.append(f"Reason: {reason}")
    if summary:
        lines.append(f"Summary: {summary}")
    meta = " | ".join(filter(None, [
        f"Confidence: {confidence}" if confidence else None,
        f"Scope: {scope}" if scope else None,
    ]))
    if meta:
        lines.append(meta)
    return "\n".join(lines)


def _mark_briefings_sent(conn, briefing_ids):
    now = datetime.now(timezone.utc)
    cur = conn.cursor()
    cur.execute(
        "UPDATE briefings SET discord_sent_at = %s WHERE id = ANY(%s)",
        (now, briefing_ids),
    )
    conn.commit()
    cur.close()


def _mark_no_sent(conn, triage_result_ids):
    now = datetime.now(timezone.utc)
    cur = conn.cursor()
    cur.execute(
        "UPDATE triage_results SET discord_no_sent_at = %s WHERE id = ANY(%s)",
        (now, triage_result_ids),
    )
    conn.commit()
    cur.close()


_DISCORD_SEND_DELAY = 0.5  # seconds between webhook POSTs to avoid rate limiting


def _post_briefings(conn, briefings, webhook_url):
    """POST briefing rows to a webhook, marking each sent immediately."""
    count = 0
    for row in briefings:
        message = _format_briefing(row)
        response = requests.post(webhook_url, json={"content": message}, timeout=10)
        response.raise_for_status()
        _mark_briefings_sent(conn, [row[0]])
        count += 1
        time.sleep(_DISCORD_SEND_DELAY)
    return count


def send_alerts(run_id=None):
    """Route unsent briefings to verdict-specific channels.

    yes       → DISCORD_WEBHOOK_URL (main channel)
    uncertain → DISCORD_UNCERTAIN_WEBHOOK_URL

    Args:
        run_id: if provided, only sends briefings from that scrape run.

    Returns:
        int: total number of briefings sent across both channels.
    """
    conn = get_connection()
    try:
        yes_briefings = _fetch_unsent_briefings(conn, 'yes', run_id)
        uncertain_briefings = _fetch_unsent_briefings(conn, 'uncertain', run_id)

        sent = 0
        if yes_briefings:
            sent += _post_briefings(conn, yes_briefings, os.environ["DISCORD_WEBHOOK_URL"])
        if uncertain_briefings:
            sent += _post_briefings(conn, uncertain_briefings, os.environ["DISCORD_UNCERTAIN_WEBHOOK_URL"])

        return sent
    finally:
        release_connection(conn)


def send_no_alerts(run_id=None):
    """Post rejected ('no') articles to the no channel as title + link.

    Args:
        run_id: if provided, only sends articles from that scrape run.

    Returns:
        int: number of articles sent (0 means nothing to send).
    """
    conn = get_connection()
    try:
        articles = _fetch_unsent_no_articles(conn, run_id)
        if not articles:
            return 0

        webhook_url = os.environ["DISCORD_NO_WEBHOOK_URL"]
        count = 0
        for (triage_result_id, title, url,
             article_flag,
             title_reason, title_confidence, title_scope,
             article_reason, article_confidence, article_scope, article_summary) in articles:
            message = _format_no_article(
                title, url, article_flag,
                title_reason, title_confidence, title_scope,
                article_reason, article_confidence, article_scope, article_summary,
            )
            response = requests.post(webhook_url, json={"content": message}, timeout=10)
            response.raise_for_status()
            _mark_no_sent(conn, [triage_result_id])
            count += 1
            time.sleep(_DISCORD_SEND_DELAY)
        return count
    finally:
        release_connection(conn)


def post_health_check(label: str, url: str, new_article_count: int) -> None:
    """Post a health check message to the health check Discord channel.

    Never raises — a health check failure must not abort the pipeline.
    """
    webhook_url = os.environ.get('DISCORD_HEALTH_CHECK_WEBHOOK_URL')
    if not webhook_url:
        logging.warning('[discord] DISCORD_HEALTH_CHECK_WEBHOOK_URL not set — skipping health check')
        return

    now = datetime.now(_LA)
    timestamp = now.strftime('%Y-%m-%d %I:%M %p %Z')
    noun = 'article' if new_article_count == 1 else 'articles'
    content = f'[{label}]({url}) {new_article_count} new {noun} — {timestamp}'

    for attempt in range(1, _HEALTH_CHECK_MAX_ATTEMPTS + 1):
        try:
            resp = requests.post(webhook_url, json={'content': content}, timeout=10)
            resp.raise_for_status()
            return
        except Exception as exc:
            if attempt < _HEALTH_CHECK_MAX_ATTEMPTS:
                time.sleep(2 ** (attempt - 1))
            else:
                logging.warning('[discord] health check failed after %d attempts: %s', _HEALTH_CHECK_MAX_ATTEMPTS, exc)
