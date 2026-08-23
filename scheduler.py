import logging

import psycopg2

from agent.scraper import run_scrape
from agent.kff_monitor import run_monitor as kff_run_monitor, FEED_URL as KFF_FEED_URL
from agent.cigna_monitor import run_monitor as cigna_run_monitor, FEED_URL as CIGNA_FEED_URL
from agent.sutter_monitor import run_monitor as sutter_run_monitor, FEED_URL as SUTTER_FEED_URL
from agent.uc_davis_monitor import run_monitor as uc_davis_run_monitor, FEED_URL as UC_DAVIS_FEED_URL
from agent.ucsd_monitor import run_monitor as ucsd_run_monitor, LISTING_URL as UCSD_LISTING_URL
from agent.uci_health_monitor import run_monitor as uci_health_run_monitor, LISTING_URL as UCI_HEALTH_LISTING_URL
from agent.ucla_health_monitor import run_monitor as ucla_health_run_monitor, LISTING_URL as UCLA_HEALTH_LISTING_URL
from agent.ucsf_monitor import run_monitor as ucsf_run_monitor, LISTING_URL as UCSF_LISTING_URL
from agent.sharp_monitor import run_monitor as sharp_run_monitor, LISTING_URL as SHARP_LISTING_URL
from agent.scripps_monitor import run_monitor as scripps_run_monitor, LISTING_URL as SCRIPPS_LISTING_URL
from agent.providence_monitor import run_monitor as providence_run_monitor, LISTING_URL as PROVIDENCE_LISTING_URL
from agent.john_muir_monitor import run_monitor as john_muir_run_monitor, LISTING_URL as JOHN_MUIR_LISTING_URL
from agent.triage import run_triage
from agent.summarizer import run_summarizer
from agent.discord import send_alerts, send_no_alerts, post_health_check, fetch_verdicts_for_articles, post_error
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
    _uc_davis_run_id, uc_davis_new_ids = uc_davis_run_monitor()
    _ucsd_run_id, ucsd_new_ids = ucsd_run_monitor()
    _uci_health_run_id, uci_health_new_ids = uci_health_run_monitor()
    _ucla_health_run_id, ucla_health_new_ids = ucla_health_run_monitor()
    _ucsf_run_id, ucsf_new_ids = ucsf_run_monitor()
    _sharp_run_id, sharp_new_ids = sharp_run_monitor()
    _scripps_run_id, scripps_new_ids = scripps_run_monitor()
    _providence_run_id, providence_new_ids = providence_run_monitor()
    _john_muir_run_id, john_muir_new_ids = john_muir_run_monitor()

    combined_ids = (beckers_new_ids + kff_new_ids + cigna_new_ids + sutter_new_ids + uc_davis_new_ids
                    + ucsd_new_ids + uci_health_new_ids + ucla_health_new_ids + ucsf_new_ids
                    + sharp_new_ids + scripps_new_ids + providence_new_ids + john_muir_new_ids)
    log.info(
        "[scheduler] %d new articles (%d Becker's, %d KFF, %d Cigna, %d Sutter, %d UC Davis, %d UCSD,"
        " %d UCI Health, %d UCLA Health, %d UCSF, %d Sharp, %d Scripps, %d Providence, %d John Muir).",
        len(combined_ids), len(beckers_new_ids), len(kff_new_ids), len(cigna_new_ids), len(sutter_new_ids),
        len(uc_davis_new_ids), len(ucsd_new_ids), len(uci_health_new_ids), len(ucla_health_new_ids),
        len(ucsf_new_ids), len(sharp_new_ids), len(scripps_new_ids), len(providence_new_ids),
        len(john_muir_new_ids),
    )

    # Becker's run_id used as the canonical pipeline run for triage/briefing records.
    flagged_ids = run_triage(combined_ids, beckers_run_id)

    post_health_check("Becker's Payer", fetch_verdicts_for_articles(beckers_new_ids),
                      web_url='https://www.beckerspayer.com/', feed_url=BECKERS_PAYER_FEED_URL)
    post_health_check("KFF Health News", fetch_verdicts_for_articles(kff_new_ids),
                      web_url='https://kffhealthnews.org/', feed_url=KFF_FEED_URL)
    post_health_check("Cigna Newsroom", fetch_verdicts_for_articles(cigna_new_ids),
                      web_url='https://newsroom.cigna.com/', feed_url=CIGNA_FEED_URL)
    post_health_check("Sutter Health", fetch_verdicts_for_articles(sutter_new_ids),
                      web_url='https://vitals.sutterhealth.org/', feed_url=SUTTER_FEED_URL)
    post_health_check("UC Davis Health", fetch_verdicts_for_articles(uc_davis_new_ids),
                      web_url='https://health.ucdavis.edu/news/', feed_url=UC_DAVIS_FEED_URL)
    post_health_check("UCSD Health", fetch_verdicts_for_articles(ucsd_new_ids),
                      web_url=UCSD_LISTING_URL, feed_url=UCSD_LISTING_URL)
    post_health_check("UCI Health", fetch_verdicts_for_articles(uci_health_new_ids),
                      web_url=UCI_HEALTH_LISTING_URL, feed_url=UCI_HEALTH_LISTING_URL)
    post_health_check("UCLA Health", fetch_verdicts_for_articles(ucla_health_new_ids),
                      web_url=UCLA_HEALTH_LISTING_URL, feed_url=UCLA_HEALTH_LISTING_URL)
    post_health_check("UCSF", fetch_verdicts_for_articles(ucsf_new_ids),
                      web_url=UCSF_LISTING_URL, feed_url=UCSF_LISTING_URL)
    post_health_check("Sharp Health", fetch_verdicts_for_articles(sharp_new_ids),
                      web_url=SHARP_LISTING_URL, feed_url=SHARP_LISTING_URL)
    post_health_check("Scripps Health", fetch_verdicts_for_articles(scripps_new_ids),
                      web_url=SCRIPPS_LISTING_URL, feed_url=SCRIPPS_LISTING_URL)
    post_health_check("Providence CA", fetch_verdicts_for_articles(providence_new_ids),
                      web_url=PROVIDENCE_LISTING_URL, feed_url=PROVIDENCE_LISTING_URL)
    post_health_check("John Muir Health", fetch_verdicts_for_articles(john_muir_new_ids),
                      web_url=JOHN_MUIR_LISTING_URL, feed_url=JOHN_MUIR_LISTING_URL)
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
    try:
        run_pipeline()
    except psycopg2.OperationalError as exc:
        msg = '⚠️ Pipeline failed — could not connect to the database.'
        if 'Connection refused' in str(exc):
            msg += ' If running locally, Docker Desktop may not be running.'
        log.error('[scheduler] %s: %s', msg, exc)
        post_error(msg)
