import os
import requests
from datetime import datetime, timezone

from db.connection import get_connection, release_connection

DIVIDER = "━━━━━━━━━━━━━━━━━━━━━━"


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


def _format_message(briefings):
    count = len(briefings)
    label = "alert" if count == 1 else "alerts"
    lines = [f"🔔 Health Insurance News — {count} new {label}", ""]

    for row in briefings:
        _, what_happened, who, impact, why_it_matters, title, url = row
        lines.append(DIVIDER)
        lines.append(f"📌 {title}")
        lines.append("")
        lines.append(f"What happened: {what_happened}")
        lines.append("")
        lines.append(f"Who's involved: {who}")
        lines.append("")
        lines.append(f"Members/revenue at stake: {impact}")
        lines.append("")
        lines.append(f"Why it matters: {why_it_matters}")
        lines.append("")
        lines.append(f"🔗 {url}")

    lines.append(DIVIDER)
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
        message = _format_message(briefings)

        response = requests.post(
            webhook_url,
            json={"content": message},
            timeout=10,
        )
        response.raise_for_status()

        briefing_ids = [row[0] for row in briefings]
        _mark_sent(conn, briefing_ids)

        return len(briefings)
    finally:
        release_connection(conn)
