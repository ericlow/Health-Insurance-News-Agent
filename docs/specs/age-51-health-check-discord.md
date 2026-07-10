# AGE-51: Health check Discord notification per scraper run

**Linear:** https://linear.app/eric-projects/issue/AGE-51

## Problem

The pipeline runs hourly but produces no observable output on quiet days when no articles are flagged. There is no way to confirm the job is alive without tailing a log file.

## Solution

After each scraper completes, post a short message to a dedicated Discord health-check channel. This is separate from the briefing channel — it is operational signal, not content.

## Behaviour

- Fires once per source immediately after the scraper returns
- Posts even when new article count is 0 — a zero-article run is proof the pipeline fired
- Two messages per pipeline run (Becker's Payer, then KFF Health News)

### Message format

```
[Becker's Payer] 3 new articles — 2026-07-10 10:00 UTC
[KFF Health News] 0 new articles — 2026-07-10 10:00 UTC
```

## Environment

| Variable | Purpose |
|---|---|
| `DISCORD_WEBHOOK_URL` | Existing — briefing notifications (unchanged) |
| `DISCORD_HEALTH_CHECK_WEBHOOK_URL` | New — health check channel |

## Implementation

### `agent/discord.py`

New function:

```python
def post_health_check(source: str, new_article_count: int) -> None:
```

- Reads `DISCORD_HEALTH_CHECK_WEBHOOK_URL` from environment
- POSTs `{"content": "[{source}] {n} new articles — {timestamp} UTC"}` to the webhook
- Logs a warning on failure, does not raise (health check failure must not abort the pipeline)

### `scheduler.py`

```python
beckers_run_id, beckers_new_ids = run_scrape()
post_health_check("Becker's Payer", len(beckers_new_ids))

_kff_run_id, kff_new_ids = run_monitor()
post_health_check("KFF Health News", len(kff_new_ids))
```

### Config files

- `.env` — add `DISCORD_HEALTH_CHECK_WEBHOOK_URL=<webhook>`
- `.env.example` — add placeholder entry
- `README.md` — add to environment variables table

## Acceptance criteria

```gherkin
Scenario: Scraper finds new articles
  Given the pipeline runs and Becker's scraper returns 3 new articles
  When scheduler.py calls post_health_check
  Then a POST is sent to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the message body contains "Becker's Payer", "3 new articles", and a UTC timestamp

Scenario: Scraper finds no new articles
  Given the pipeline runs and KFF scraper returns 0 new articles
  When scheduler.py calls post_health_check
  Then a POST is still sent to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the message body contains "KFF Health News" and "0 new articles"

Scenario: Health check webhook call fails
  Given DISCORD_HEALTH_CHECK_WEBHOOK_URL is misconfigured
  When post_health_check is called
  Then the error is logged as a warning
  And the pipeline continues without raising
```

## Out of scope

- Aggregating health checks into a single end-of-run summary (one message per source keeps failures attributable)
- Retry logic on webhook failure
- Alerting on repeated failures (future work)
