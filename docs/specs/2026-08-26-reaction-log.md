# Spec: Discord Reaction Log

_Status: draft_
_Last updated: 2026-08-26_

---

## Background — Why This Exists

The triage agent uses a prompt-as-judge to decide which articles to surface. The prompt
is based on Matt's stated preferences ("network changes, acquisitions, TPA shifts"). But
Matt's actual reading behavior diverges from his stated preferences — several articles per
week are surfaced; he reads one or two. He cannot fully articulate why he skips the rest.

This is a revealed preference problem. Stated preferences produce the wrong filter. Actual
behavior is the ground truth.

A 👍 reaction on a Discord message is the lowest-friction signal Matt can give. He is
already reading the messages; one tap records his judgment. Over time, the reaction log
becomes a labeled dataset: articles Matt actually found worth reading vs. articles he
ignored. This is more reliable training signal than any prompt.

**V1 goal:** collect the signal. No model training, no triage changes. Just log reactions
faithfully so the dataset exists when it is needed.

**Future use:** evaluate triage recall (what fraction of liked articles were surfaced?),
tune relevance scoring, eventually replace or augment the prompt-as-judge with a model
trained on real behavior.

---

## User Story

As Eric (system operator), I want the system to automatically record when Matt 👍-reacts
to a bot message in the Discord channel, so that over time I have a ground-truth record
of which surfaced articles Matt found worth reading.

---

## Acceptance Criteria

1. A scheduled job runs every 4 hours and scans recent bot messages in the channel for 👍 reactions
2. Each new 👍 reaction is written to the DB: URL, message text, reactor user ID, timestamp
3. Reactions already recorded are not duplicated
4. The job handles the case where a message contains no URL gracefully — it logs the message text but leaves the URL field null
5. The job runs without human intervention; failures are logged but do not alert

---

## Technical Design

### Data Model

```yaml
table: reaction_log
columns:
  id:           SERIAL PRIMARY KEY
  message_id:   TEXT NOT NULL              # Discord message snowflake ID
  channel_id:   TEXT NOT NULL              # Discord channel ID
  url:          TEXT                       # first URL extracted from message text; null if none
  message_text: TEXT NOT NULL              # full text of the reacted message (for context)
  reactor_id:   TEXT NOT NULL              # Discord user ID of the person who reacted
  reacted_at:   TIMESTAMPTZ NOT NULL       # when the reaction was added
  logged_at:    TIMESTAMPTZ NOT NULL DEFAULT now()

constraints:
  unique: (message_id, reactor_id)         # one row per person per message; no duplicates
```

### Job Logic

```
1. Post to system channel: "Reaction log job started — scanning last 100 messages"

2. Fetch recent messages from the bot's channel via Discord API
   GET /channels/{channel_id}/messages?limit=100
   Filter: only messages authored by the bot (author.bot == true)

3. For each bot message:
   GET /channels/{channel_id}/messages/{message_id}/reactions/👍
   Returns list of users who reacted

4. For each reactor on each message:
   Extract first URL from message_text
   INSERT INTO reaction_log (...) VALUES (...) ON CONFLICT (message_id, reactor_id) DO NOTHING
   Count whether the INSERT was a new row or a skip

5. Post to system channel:
   "Reaction log job complete — {new} new reactions logged, {skipped} already seen,
   {messages} messages scanned"
```

**Idempotency:** step 4 uses `INSERT ... ON CONFLICT DO NOTHING` on the unique constraint
`(message_id, reactor_id)`. Already-logged reactions are silently skipped — no error, no
duplicate. The job is safe to run multiple times.

**Author filter:** bot messages are identified by `author.bot == true` in the Discord API
response, not by application ID. Webhook-posted messages set this flag correctly.

### URL Extraction

Extract the first `https://` URL from the message text using a simple regex. The bot's
"Found:" messages contain markdown links in the form `[title](url)` — extract the URL
from the parentheses. If no URL is present, store null.

### Schedule

Every 4 hours. Aligns with A1's 8-hour scrape cycle, catching reactions added since the
last run. Can be run manually at any time without side effects (idempotent).

### Execution

Lambda function or standalone script. Given the job's simplicity (HTTP calls + DB writes,
no LLM), a standalone Python script on a cron schedule is sufficient for v1. Migrate to
Lambda when the rest of the infrastructure moves.

### Configuration

| Env var | Description |
|---|---|
| `DISCORD_BOT_TOKEN` | Bot token for API access (already in Lambda env) |
| `DISCORD_CHANNEL_ID` | The channel ID to scan — must be set explicitly |
| `DATABASE_URL` | Neon connection string (already in Lambda env) |

`DISCORD_CHANNEL_ID` is not currently stored as a named env var — it arrives dynamically
in interaction payloads. For this job it must be hardcoded in config or added to the
environment.

---

## What the Data Enables (Future)

This spec only covers collection. These are not v1 deliverables.

**Triage recall audit:** for any time window, join `reaction_log` against `articles` and
`triage_results` to ask: of the articles Matt liked, what fraction did the triage agent
surface? What fraction did it miss? This answers whether the prompt is too loose (many
surfaced, few liked) or too tight (liked articles not surfaced).

**Few-shot prompt improvement:** the 👍 articles become positive examples for the triage
prompt. The surfaced-but-ignored articles (present in `triage_results` but absent from
`reaction_log`) become negative examples. Both sets can be fed to the triage prompt as
labeled examples to tighten the filter without changing the model.

**Preference modeling:** with enough reactions, train or fine-tune a classifier on
article text → liked/not-liked. Replace the prompt-as-judge entirely.

---

## Scenarios

```gherkin
Scenario: New reaction is logged
  Given the bot posted a message containing a URL in the channel
  And Matt reacted with 👍 to that message
  And no row exists in reaction_log for (message_id, Matt's user_id)
  When the job runs
  Then a new row is inserted into reaction_log with the URL and timestamp

Scenario: Duplicate reaction is skipped
  Given a row already exists in reaction_log for (message_id, Matt's user_id)
  When the job runs again
  Then no duplicate row is inserted
  And the job completes without error

Scenario: Message has no URL
  Given the bot posted a message with no URL (e.g. a status line like "Searching: ...")
  And a user reacted with 👍
  When the job runs
  Then a row is inserted with url = null and the full message_text stored

Scenario: Job runs when no new reactions exist
  Given no new 👍 reactions have been added since the last run
  When the job runs
  Then no rows are inserted
  And the job exits cleanly with a log line noting zero new reactions

Scenario: Discord API rate limit hit
  Given the Discord API returns 429 during the scan
  When the job encounters the error
  Then it logs the error and exits without partial writes
  And the next scheduled run retries from scratch (idempotent)
```

---

## Out of Scope

- Other emoji reactions — only 👍 is tracked in v1; extend to other signals when the use
  case is clear
- Reactions on non-bot messages — only the bot's own messages are scanned
- Real-time reaction detection via Discord gateway — polling is sufficient at this volume
- Removing logged reactions when a user un-reacts — the log is append-only; a removed
  reaction is not a retraction of interest
- Any model training, prompt changes, or triage tuning — v1 is data collection only
