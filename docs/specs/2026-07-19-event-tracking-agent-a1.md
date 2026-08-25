# A1: Event Tracking Agent

_Status: ready for implementation_
_Last updated: 2026-07-19_
_Linear: [AGE-67](https://linear.app/eric-projects/issue/AGE-67/spec-event-tracking-agent-a1-named-party-monitor-conversational)_

---

## Background

The existing pipeline monitors broad health insurance industry news. A1 adds targeted tracking of a specific relationship between two named parties (e.g., Sutter Health and Anthem) — watching for termination events, contract disputes, network exits, or any meaningful development between them.

A1 has two parts:
1. **Monitor** — scrapes Google News and existing sources for articles about the watched pair; notifies via Discord when triage-filtered articles are found
2. **Conversational agent** — lets the user ask questions about collected articles in Discord; accumulates context over time

---

## Problem

The analyst needs to track the evolving relationship between two specific parties over weeks or months. The existing pipeline surfaces broad industry news but has no mechanism for sustained, targeted monitoring of a named relationship.

---

## Solution

A `watched_pairs` table in Neon stores entity pairs and their aliases. On each run, A1 searches existing collected articles and triggers a fresh scrape for each active pair. Triage-passing articles are posted to Discord. The user can reply in Discord to ask questions; the conversational agent answers using all collected articles for that pair, and persists added context to Neon.

---

## Data model

### `watched_pairs` table

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `party_a` | text | Canonical name (e.g., "Sutter Health") |
| `party_a_aliases` | text[] | All known names (e.g., ["Sutter Health", "Alta Bates Summit", "PAMF"]) |
| `party_b` | text | Canonical name (e.g., "Anthem") |
| `party_b_aliases` | text[] | All known names (e.g., ["Anthem", "Elevance Health", "Anthem Blue Cross"]) |
| `active` | boolean | Whether this pair is currently being monitored |
| `created_at` | timestamptz | |

### `pair_articles` table

Links articles to watched pairs (many-to-many).

| Column | Type | Notes |
|---|---|---|
| `pair_id` | uuid | FK → watched_pairs |
| `article_id` | uuid | FK → articles |
| `found_via` | text | `"db_search"` or `"fresh_scrape"` |
| `triage_verdict` | text | `"yes"` / `"uncertain"` / `"no"` |
| `created_at` | timestamptz | |

### `pair_context` table

Persists context added by the user during conversations.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `pair_id` | uuid | FK → watched_pairs |
| `content` | text | Free-form context (e.g., "Contract expires March 2027 per source") |
| `added_at` | timestamptz | |

### `pair_conversations` table

Persists conversation history per pair.

| Column | Type | Notes |
|---|---|---|
| `id` | uuid | Primary key |
| `pair_id` | uuid | FK → watched_pairs |
| `role` | text | `"user"` or `"assistant"` |
| `content` | text | Message content |
| `created_at` | timestamptz | |

---

## Article retrieval — two paths

For each active watched pair on each run:

**Path 1 — DB search**
Query existing `articles` table for rows where `body_text` or `title` contains aliases from both party lists:
```sql
SELECT * FROM articles
WHERE (body_text ILIKE ANY('{%Sutter Health%,%Alta Bates%,%PAMF%}'))
AND   (body_text ILIKE ANY('{%Anthem%,%Elevance Health%,%Anthem Blue Cross%}'))
AND   id NOT IN (SELECT article_id FROM pair_articles WHERE pair_id = ?)
```

**Path 2 — Fresh scrape**
Build a Google News query from alias lists:
```
("Sutter Health" OR "Alta Bates" OR "PAMF") AND ("Anthem" OR "Elevance Health" OR "Anthem Blue Cross")
```
Fetch RSS feed, resolve canonical URLs, save new articles to `articles` table, link to pair in `pair_articles`.

Both paths share the existing Google News scraper code (AGE-64). The fresh scrape is a parameterized call with a per-pair query rather than the global query.

---

## Triage

Each article found via either path is triaged using the existing triage prompt, with additional context: the pair being watched and the type of events to flag (termination, contract dispute, network exit, acquisition, partnership change). Verdict stored in `pair_articles.triage_verdict`.

Only `yes` verdicts trigger a Discord notification.

---

## Notifications

When triage-passing articles are found for a pair, post to the existing Discord briefing channel:

```
[Sutter Health ↔ Anthem] 2 new articles — 2026-07-19 08:00 AM PDT
✅ [Sutter Health warns of Anthem network exit amid contract talks](https://...)
✅ [Anthem members face disruption as Sutter negotiations stall](https://...)
```

---

## Conversational interface

The user can reply to any A1 Discord message to start a conversation. Each reply triggers a Lambda invocation (via API Gateway + Discord webhook) that:

1. Loads all `pair_articles` (triage-passing) for the pair
2. Loads `pair_context` for the pair
3. Loads recent `pair_conversations` history
4. Calls Claude with full context
5. Posts the response to Discord
6. Saves the new conversation turns to `pair_conversations`

If the user adds new context ("remember that the contract expires in March"), the agent extracts it and writes a row to `pair_context`.

---

## Shared code

The fresh scrape path reuses the existing Google News scraper module (AGE-64). The per-pair query replaces the global `google_news_query` config value. No changes to the existing global monitor — they run independently.

---

## Acceptance criteria

```gherkin
Scenario: Monitor finds new articles for a watched pair via DB search
  Given a watched pair (Sutter Health ↔ Anthem) is active
  And an existing article mentions "Sutter Health" and "Anthem" in body_text
  And the article is not already linked to this pair
  When the A1 monitor runs
  Then the article is linked to the pair in pair_articles
  And the article is triaged with pair context

Scenario: Monitor finds new articles via fresh scrape
  Given a watched pair (Sutter Health ↔ Anthem) is active
  When the A1 monitor runs
  Then a Google News RSS query is built from party_a_aliases and party_b_aliases
  And new articles are saved to the articles table and linked to the pair

Scenario: Triage-passing article triggers Discord notification
  Given a pair article receives triage verdict "yes"
  Then a Discord notification is posted with the pair name, article title, and URL

Scenario: User replies to Discord notification
  Given a Discord notification was posted for Sutter Health ↔ Anthem
  When the user replies "what's the latest on this?"
  Then the conversational agent loads all pair articles and context
  And posts a response to Discord
  And saves the conversation turn to pair_conversations

Scenario: User adds context during conversation
  Given the user says "the contract expires in March 2027"
  Then the agent writes a row to pair_context with that content
  And acknowledges the context was saved
```

---

## Out of scope

- Web UI or CLI conversational interface (Discord only)
- Email notifications
- Press release website scraping (future — alias lists are already structured to support it)
- Managing watched pairs via the conversational agent (future)
- A2 analysis agent integration (separate spec)
