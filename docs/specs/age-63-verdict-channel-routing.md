# AGE-63: Route articles to verdict-specific Discord channels

[AGE-63](https://linear.app/eric-projects/issue/AGE-63/route-articles-to-verdict-specific-discord-channels)

## Background / WHY

The triage pipeline classifies every article as `yes`, `uncertain`, or `no` and stores all three
verdicts in `triage_results`. Currently `yes` and `uncertain` briefings are both posted to the same
main Discord channel; `no` articles are never surfaced to the analyst at all.

Routing each verdict to its own channel gives the analyst a full picture of what the system saw and
decided — making it easier to audit triage quality, spot misclassifications, and calibrate the prompt
over time.

## User story

As an analyst, I want uncertain and rejected articles posted to dedicated Discord channels so I can
review the triage signal across all three verdict classes without mixing them on the main feed.

## Acceptance criteria (Gherkin)

**Scenario: yes article posted to main channel (unchanged)**
```
Given an article is triaged "yes"
When the pipeline runs
Then a 4-field briefing is posted to the main Discord channel
And the article is NOT posted to the uncertain or no channel
```

**Scenario: uncertain article posted to uncertain channel only**
```
Given an article is triaged "uncertain"
When the pipeline runs
Then a 4-field briefing is posted to the uncertain Discord channel
And the article is NOT posted to the main channel
```

**Scenario: no article posted to no channel**
```
Given an article is triaged "no" (at title or article stage)
When the pipeline runs
Then the article title and URL are posted to the no Discord channel
And no briefing is generated for this article
```

**Scenario: already-sent articles are not re-sent**
```
Given an article has been sent to its verdict channel in a prior run
When the pipeline runs again
Then no duplicate message is posted
```

**Scenario: run with no new articles produces no posts**
```
Given all articles from a run have already been sent
When the pipeline runs
Then no messages are posted to any channel
```

## Discord message formats

**Main channel (`yes`)** — unchanged, existing 4-field briefing format.

**Uncertain channel** — same 4-field briefing format as main channel.

**No channel:**
```
[Article Title](https://url-to-article)
```

## Implementation decisions

| # | Decision | Choice |
|---|----------|--------|
| 1 | Tracking sent state for `no` articles | Add `discord_no_sent_at TIMESTAMPTZ` column to `triage_results` |
| 2 | Routing briefings by verdict | Join `briefings` → `triage_results` on `article_flag` to determine which webhook to use |
| 3 | Env var names for new webhooks | `DISCORD_UNCERTAIN_WEBHOOK_URL`, `DISCORD_NO_WEBHOOK_URL` |
| 4 | Code location | Extend `agent/discord.py` — all Discord logic stays in one module |

## Schema change

```sql
ALTER TABLE triage_results
    ADD COLUMN discord_no_sent_at TIMESTAMPTZ;
```

## Out of scope

- Changing the triage prompt or classification logic
- Retroactively posting previously-processed `no` or `uncertain` articles
- Reaction/feedback tracking on Discord messages
- Any change to the health check webhook
