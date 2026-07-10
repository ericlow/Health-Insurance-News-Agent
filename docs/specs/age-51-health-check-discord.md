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
- Retries on transient failure before giving up
- After all retries are exhausted, logs a warning and continues — health check failure must not abort the pipeline

### Message format

```
[Becker's Payer] 3 new articles — 2026-07-10 10:00 AM PDT
[KFF Health News] 0 new articles — 2026-07-10 10:00 AM PDT
```

Timestamp is expressed in America/Los_Angeles time (PST/PDT depending on DST).

## Environment

| Variable | Purpose |
|---|---|
| `DISCORD_WEBHOOK_URL` | Existing — briefing notifications (unchanged) |
| `DISCORD_HEALTH_CHECK_WEBHOOK_URL` | New — health check channel |

## Acceptance criteria

```gherkin
Scenario: Scraper finds new articles
  Given the pipeline runs and Becker's scraper returns 3 new articles
  Then a health check message is posted to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the message contains "Becker's Payer", "3 new articles", and a Los Angeles timezone timestamp

Scenario: Scraper finds no new articles
  Given the pipeline runs and KFF scraper returns 0 new articles
  Then a health check message is still posted to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the message contains "KFF Health News" and "0 new articles"

Scenario: Health check post fails transiently
  Given the webhook POST returns a server error
  Then the post is retried
  And if all retries are exhausted, the error is logged as a warning
  And the pipeline continues without raising
```

## Out of scope

- Aggregating health checks into a single end-of-run summary (one message per source keeps failures attributable)
- Alerting on repeated failures (future work)
