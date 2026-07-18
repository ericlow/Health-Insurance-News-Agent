import logging

from agent.scraper import run_scrape
from agent.kff_monitor import run_monitor as kff_run_monitor, FEED_URL as KFF_FEED_URL
from agent.cigna_monitor import run_monitor as cigna_run_monitor, FEED_URL as CIGNA_FEED_URL
from agent.sutter_monitor import run_monitor as sutter_run_monitor, FEED_URL as SUTTER_FEED_URL
from agent.triage import run_triage
from agent.summarizer import run_summarizer
from agent.discord import send_alerts, send_no_alerts, post_health_check, fetch_verdicts_for_articles
from config import BECKERS_PAYER_FEED_URL

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)


def run_pipeline():
    """Execute one full monitor-triage-brief-alert pipeline run."""
    log.info('[scheduler] Starting pipeline run.')

    beckers_run_id, beckers_new_ids = run_scrape()
    _kff_run_id, kff_new_ids = kff_run_monitor()
    _cigna_run_id, cigna_new_ids = cigna_run_monitor()
    _sutter_run_id, sutter_new_ids = sutter_run_monitor()

    combined_ids = beckers_new_ids + kff_new_ids + cigna_new_ids + sutter_new_ids
    log.info(
        "[scheduler] %d new articles (%d Becker's, %d KFF, %d Cigna, %d Sutter).",
        len(combined_ids), len(beckers_new_ids), len(kff_new_ids), len(cigna_new_ids), len(sutter_new_ids),
    )

    # Becker's run_id used as the canonical pipeline run for triage/briefing records.
    flagged_ids = run_triage(combined_ids, beckers_run_id)

    post_health_check("Becker's Payer", fetch_verdicts_for_articles(beckers_new_ids))
    post_health_check("KFF Health News", fetch_verdicts_for_articles(kff_new_ids))
    post_health_check("Cigna Newsroom", fetch_verdicts_for_articles(cigna_new_ids))
    post_health_check("Sutter Health", fetch_verdicts_for_articles(sutter_new_ids))
    log.info('[scheduler] %d articles flagged for briefing.', len(flagged_ids))

    briefing_ids = run_summarizer(flagged_ids, beckers_run_id)
    log.info('[scheduler] %d briefings created.', len(briefing_ids))

    sent = send_alerts()
    if sent:
        log.info('[scheduler] Discord alert posted (%d briefings).', sent)
    else:
        log.info('[scheduler] No alerts to send this run.')

    no_sent = send_no_alerts()
    if no_sent:
        log.info('[scheduler] Discord no-channel posted (%d articles).', no_sent)

    log.info('[scheduler] Pipeline run complete.')


if __name__ == '__main__':
    run_pipeline()
