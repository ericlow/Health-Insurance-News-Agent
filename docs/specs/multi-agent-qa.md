# Multi-Agent Conversational Q&A — Feature Spec

_Status: draft_
_Last updated: 2026-07-16_

---

## Background

A known high-stakes story is developing: Stanford Hospital and Cigna are heading
toward a network termination in approximately 2 months. The analyst needs to track
this story as it evolves — new articles appear over weeks, signals shift, and the
outcome is uncertain.

The system already scrapes and triages articles. What's missing is the ability to
ask the system questions and get grounded, cited answers as the knowledge base grows.

Three competing agents will answer each question using different strategies, and the
analyst evaluates which performs best. This creates a feedback loop for improving
agent design over time.

**Why now:** Building this as a portfolio piece demonstrating multi-agent design,
RAG, tool use, and human-in-the-loop evaluation patterns. Genuine project value
overlaps — the analyst actually needs this capability for the Stanford/Cigna story.

---

## User Story

As a health insurance analyst tracking a developing story (e.g. Stanford/Cigna
network termination),
I want to ask the Discord bot questions and receive cited answers from multiple agents,
so that I can get the most reliable answer and identify which agent strategy is most
trustworthy over time.

---

## Design Principle: Story-Specific Proactive Monitoring

When a story is registered, the system automatically creates a targeted news monitor
for that story — not just relying on the general Becker's/KFF feeds.

**Google News RSS** supports search queries and is the primary mechanism:
```
https://news.google.com/rss/search?q=Stanford+Cigna+network+termination&hl=en-US&gl=US&ceid=US:en
```

The query is generated from the story's entity pair + event type at registration time
(e.g. entity_1="Stanford", entity_2="Cigna", event_type="network termination" →
query string constructed by the bot).

This monitor runs on the same hourly schedule as the general scraper. Articles found
are stored in the `articles` table and automatically linked to the story — they
bypass general triage (they're already targeted) and go directly into the
story-matching pipeline.

### Open questions added for next session

| # | Question | Status |
|---|----------|--------|
| Q7 | How is the Google News query string generated — rule-based from entity fields, or LLM-generated? | Open |
| Q8 | Do Google News articles go through triage or bypass it? | Open |

---

## Design Principle: Multi-Turn Conversation

Agents support ongoing dialog about a story — not just one-shot Q&A. The exec can
ask follow-up questions that reference prior turns:

> "What's the latest on Stanford/Cigna?"
> "How does that compare to what you said last week?"
> "What's Cigna's revenue exposure if this falls through?"

Each agent receives the full conversation history for the story as context when
answering. Prior questions, answers, and declared winners are all visible — agents
can build on, revise, or contrast with earlier responses.

### Conversations table (new)

```sql
CREATE TABLE conversation_turns (
    id              SERIAL PRIMARY KEY,
    story_id        INTEGER NOT NULL REFERENCES stories(id),
    question        TEXT NOT NULL,
    response_a      TEXT,
    response_b      TEXT,
    response_c      TEXT,
    winner          TEXT CHECK (winner IN ('A', 'B', 'C')),
    asked_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Discord threads are the natural container for a conversation — each story gets a
thread, and turns accumulate there.

---

## Design Principle: News-Aware Agents

When the exec asks a question, each agent must incorporate newly arrived articles
as part of its answer context — not just the historical baseline. An article linked
to a story 2 hours ago is as relevant as one linked 2 weeks ago.

This means:
- **Agent A** — searches the live article index at question time; new articles are
  automatically included as they are linked
- **Agent B** — the case file must be updated each time a new article is linked to
  the story; the agent answers from the current synthesis, not a stale snapshot
- **Agent C** — uses recent article timestamps to scope external data fetches
  (e.g. "what's changed since the last article was published?")

Additionally, agents may proactively surface newly arrived articles when they are
directly relevant to the question being asked: "Note: a new article was linked to
this story 3 hours ago — here is how it affects this answer."

---

## The Three Agents

### Agent A — Index + Search (RAG)
At question time, searches stored articles using keyword or vector search. Composes
an answer from retrieved passages. Cites source articles.

- Bounded by what was scraped
- Low hallucination risk
- Answers degrade if no relevant articles exist

### Agent B — Living Document (Case File)
Maintains a structured "case file" for the story that is updated each time a new
relevant article is scraped. At question time, answers from the synthesis.

- More agentic — the agent is actively maintaining state over time
- Faster at question time (no search step)
- Risk: synthesis errors compound if case file is updated incorrectly

### Agent C — Multi-Step Tool Use + External Grounding
At question time, plans what it needs, then actively fetches from public sources:
CMS enrollment data, SEC/EDGAR filings, CHHS open data portal. Synthesizes answer
from internal articles + external data.

- Richest answers — can answer what articles don't cover (e.g. member counts,
  revenue at stake)
- Highest complexity and latency
- More surface area for errors

---

## Evaluation

The exec (principal) sees all three responses and declares a winner per question.
Preferences are stored. No automated metric in v1 — human-in-the-loop judgment only.

---

## Story Registration

The analyst registers a story by @-mentioning the bot in natural language:

> "Stanford and Cigna are terminating relationship in 3 months. Monitor this."

The bot parses the message, extracts entity pair + event type + timeline, creates a
story record, and confirms registration.

### Stories table (new)

```sql
CREATE TABLE stories (
    id              SERIAL PRIMARY KEY,
    entity_1        TEXT NOT NULL,          -- e.g. "Stanford Health Care"
    entity_2        TEXT NOT NULL,          -- e.g. "Cigna"
    event_type      TEXT NOT NULL,          -- e.g. "network termination"
    expected_date   DATE,                   -- analyst's estimate, nullable
    description     TEXT,                   -- full natural language input
    registered_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Article-to-story linking

Linking articles to stories is a **separate, independently re-runnable pipeline** —
decoupled from scraping and triage. This allows:
- Swapping the matching strategy without reprocessing unrelated data
- Reprocessing all historical articles against a newly registered story
- Experimenting with different matchers (keyword, LLM-as-judge, hybrid) side-by-side

The matcher is a pluggable interface. v1 will implement at least one strategy;
others can be added without changing the pipeline contract.

```sql
CREATE TABLE article_stories (
    article_id      INTEGER NOT NULL REFERENCES articles(id),
    story_id        INTEGER NOT NULL REFERENCES stories(id),
    linked_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    matcher         TEXT NOT NULL,   -- e.g. "keyword_v1", "haiku_judge_v1"
    confidence      REAL,            -- optional, 0.0-1.0
    PRIMARY KEY (article_id, story_id, matcher)
);
```

The composite primary key `(article_id, story_id, matcher)` allows multiple matchers
to independently link the same article to the same story — useful for comparison.

### Agent B case file table

```sql
CREATE TABLE case_files (
    id          SERIAL PRIMARY KEY,
    story_id    INTEGER NOT NULL REFERENCES stories(id),
    content     TEXT NOT NULL,      -- synthesized markdown brief
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### Agent C — External Sources

| Source | What it provides | Notes |
|--------|-----------------|-------|
| CMS | Enrollment data, plan participation, Medicare/Medicaid membership | Public API |
| SEC/EDGAR | Financial filings, revenue, membership counts | Public companies only (Cigna yes, Stanford no) |
| CHHS (`data.chhs.ca.gov`) | California health data, plan enrollment | Public API |
| IRS Form 990 | Revenue, expenses for nonprofit health systems | Stanford files as nonprofit |
| OSHPD/HCAI | California hospital financial + utilization data | State-mandated filings |
| AHD.com (`ahd.com/data_services.html`) | Hospital financial and operational data | Tentative — review data access model before building |

Agent C selects which sources to query based on the question. Not all sources are
called for every question — the planning step (Opus) decides which are relevant.

---

### Feedback table

```sql
CREATE TABLE agent_preferences (
    id              SERIAL PRIMARY KEY,
    story_id        INTEGER NOT NULL REFERENCES stories(id),
    question        TEXT NOT NULL,
    winner          TEXT NOT NULL CHECK (winner IN ('A', 'B', 'C')),
    response_a      TEXT,
    response_b      TEXT,
    response_c      TEXT,
    asked_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

---

## Open Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Does the analyst explicitly register a story to track? | **Decided — yes. Natural language @-mention: "Stanford and Cigna are terminating in 3 months. Monitor this."** |
| Q2 | How are new articles linked to a registered story? | **Decided — separate re-runnable pipeline with pluggable matcher interface. `article_stories` stores matcher name so multiple strategies can coexist and be compared.** |
| Q3 | How are three answers presented in Discord? Sequential messages? Single formatted embed? | **Deferred — cheap to change. Start with sequential (one message per agent), revisit after first working version.** |
| Q4 | How does the exec declare a winner? | **Decided — reply-based. Exec replies "A", "B", or "C" after seeing three responses. Bot records the preference.** |
| Q5 | What external sources does Agent C hit? | **Decided (tentative) — see Agent C Sources section below.** |
| Q6 | Is the system general-purpose (any entity pair) from the start, or Stanford/Cigna only for v1? | **Decided — general-purpose from the start. Stories table is already parameterized; no hardcoding.** |

---

## Out of Scope (v1)

- Auto-detection of topics from article stream (Q1 above — dedup unvalidated)
- Automated winner selection / A-B test scoring
- Multiple simultaneous tracked stories (unless Q5 resolved)
- Agent C writing back enriched data to the articles table

---

## Next Steps

1. Resolve Q1 (topic registration) — gates data model
2. Resolve Q2/Q3 (Discord UX) — gates Discord component design
3. Draft Gherkin scenarios
4. Define data model (stories table, case_file table for Agent B, feedback/preferences table)
5. Define component map and sequence diagrams
