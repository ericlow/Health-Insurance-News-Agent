import logging

from agent.scraper import run_scrape
from agent.kff_monitor import run_monitor
from agent.triage import run_triage
from agent.summarizer import run_summarizer
from agent.discord import send_alerts

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
)
log = logging.getLogger(__name__)


def run_pipeline():
    """Execute one full monitor-triage-brief-alert pipeline run."""
    log.info('[scheduler] Starting pipeline run.')

    beckers_run_id, beckers_new_ids = run_scrape()
    _kff_run_id, kff_new_ids = run_monitor()

    combined_ids = beckers_new_ids + kff_new_ids
    log.info(
        '[scheduler] %d new articles (%d Becker\'s, %d KFF).',
        len(combined_ids), len(beckers_new_ids), len(kff_new_ids),
    )

    # Becker's run_id used as the canonical pipeline run for triage/briefing records.
    flagged_ids = run_triage(combined_ids, beckers_run_id)
    log.info('[scheduler] %d articles flagged for briefing.', len(flagged_ids))

    briefing_ids = run_summarizer(flagged_ids, beckers_run_id)
    log.info('[scheduler] %d briefings created.', len(briefing_ids))

    sent = send_alerts()
    if sent:
        log.info('[scheduler] Discord alert posted (%d briefings).', sent)
    else:
        log.info('[scheduler] No alerts to send this run.')

    log.info('[scheduler] Pipeline run complete.')


if __name__ == '__main__':
    run_pipeline()
