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


def _fetch_unsent_briefings(conn, run_id=None):
    cur = conn.cursor()
    if run_id is not None:
        cur.execute(
            """
            SELECT b.id, b.what_happened, b.who, b.impact, b.why_it_matters,
                   a.title, a.url
            FROM briefings b
            JOIN articles a ON a.id = b.article_id
            WHERE b.discord_sent_at IS NULL
              AND b.scrape_run_id = %s
            ORDER BY b.created_at
            """,
            (run_id,),
        )
    else:
        cur.execute(
            """
            SELECT b.id, b.what_happened, b.who, b.impact, b.why_it_matters,
                   a.title, a.url
            FROM briefings b
            JOIN articles a ON a.id = b.article_id
            WHERE b.discord_sent_at IS NULL
            ORDER BY b.created_at
            """
        )
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


def _mark_sent(conn, briefing_ids):
    now = datetime.now(timezone.utc)
    cur = conn.cursor()
    cur.execute(
        "UPDATE briefings SET discord_sent_at = %s WHERE id = ANY(%s)",
        (now, briefing_ids),
    )
    conn.commit()
    cur.close()


def send_alerts(run_id=None):
    """Query unsent briefings, format, POST to Discord, mark delivered.

    Args:
        run_id: if provided, only sends briefings from that scrape run.
                if None, sends all unsent briefings (useful for manual runs).

    Returns:
        int: number of briefings sent (0 means nothing to send).
    """
    conn = get_connection()
    try:
        briefings = _fetch_unsent_briefings(conn, run_id)
        if not briefings:
            return 0

        webhook_url = os.environ["DISCORD_WEBHOOK_URL"]
        sent_ids = []
        for row in briefings:
            message = _format_briefing(row)
            response = requests.post(
                webhook_url,
                json={"content": message},
                timeout=10,
            )
            response.raise_for_status()
            sent_ids.append(row[0])

        _mark_sent(conn, sent_ids)

        return len(briefings)
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
