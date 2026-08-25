# AGE-51: Health check Discord notification per scraper run

**Linear:** https://linear.app/eric-projects/issue/AGE-51

## Problem

The pipeline runs hourly but produces no observable output on quiet days when no articles are flagged. There is no way to confirm the job is alive without tailing a log file.

## Solution

After triage completes, post a health check block per source to a dedicated Discord health-check channel. Each block shows the source name, article count, timestamp, and the triage verdict for every new article. This is separate from the briefing channel — it is operational signal, not content.

## Behaviour

- One block per source, posted after triage runs (not immediately after scraping)
- Posts even when new article count is 0 — a zero-article run is proof the pipeline fired
- Four blocks per pipeline run (Becker's Payer, KFF Health News, Cigna Newsroom, Sutter Health)
- Each new article appears as a clickable title link with a verdict emoji prefix
- Retries on transient failure before giving up
- After all retries are exhausted, logs a warning and continues — health check failure must not abort the pipeline

### Message format

Non-zero run:
```
[Becker's Payer] 3 new articles — 2026-07-18 10:00 AM PDT
✅ [Cigna exits Humana network in three California counties](https://beckers.com/...)
❓ [UHC revenue misses expectations amid rising medical claims](https://beckers.com/...)
❌ [FDA approves new GLP-1 drug for obesity treatment](https://beckers.com/...)
```

Zero-article run (header only):
```
[KFF Health News] 0 new articles — 2026-07-18 10:00 AM PDT
```

### Verdict emoji key

| Verdict | Emoji |
|---|---|
| `yes` | ✅ |
| `uncertain` | ❓ |
| `no` | ❌ |

Timestamp is expressed in America/Los_Angeles time (PST/PDT depending on DST).

## Data requirements

`post_health_check` must receive the article rows for that source — each row needs: title, URL, and triage verdict. The scheduler passes these after `run_triage` returns.

## Environment

| Variable | Purpose |
|---|---|
| `DISCORD_WEBHOOK_URL` | Existing — briefing notifications (unchanged) |
| `DISCORD_HEALTH_CHECK_WEBHOOK_URL` | New — health check channel |

## Acceptance criteria

```gherkin
Scenario: Scraper finds new articles and triage has run
  Given the pipeline runs and Becker's scraper returns 3 new articles
  And triage has assigned verdicts: yes, uncertain, no
  Then a health check block is posted to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the header contains "Becker's Payer", "3 new articles", and a Los Angeles timezone timestamp
  And each article appears as "✅ [title](url)", "❓ [title](url)", or "❌ [title](url)"

Scenario: Scraper finds no new articles
  Given the pipeline runs and KFF scraper returns 0 new articles
  Then a health check block is still posted to DISCORD_HEALTH_CHECK_WEBHOOK_URL
  And the message contains "KFF Health News" and "0 new articles"
  And no article lines are included

Scenario: Health check post fails transiently
  Given the webhook POST returns a server error
  Then the post is retried
  And if all retries are exhausted, the error is logged as a warning
  And the pipeline continues without raising
```

## Out of scope

- Aggregating health checks into a single end-of-run summary (one block per source keeps failures attributable)
- Alerting on repeated failures (future work)
- Article count breakdown by verdict in the header (e.g., "1 yes · 1 maybe · 1 no")
