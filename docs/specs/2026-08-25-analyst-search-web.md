# AnalystAgent — `search_web` Tool — Feature Spec

_Status: draft_
_Last updated: 2026-08-25_

---

## Background

The AnalystAgent's first tool, `fetch_url`, needs a URL to work. But the agent often
starts from an *event*, not a link. In AGE-71, 4 of 12 sources were found by web
search, and Matt's stated first step on any new event is "I'd start with a google
search." `search_web` is how the agent turns a rules-layer hint ("Covered CA publishes
an SB-260 county table") or a vague event description into concrete URLs it can then
`fetch_url`. Without it, the agent can only analyze pages Matt hands it directly.

This is the **second tool** in the Claude tool-loop, added after the real engine
(`fetch_url` loop, AGE-95). It slots into the same loop — no new execution machinery.

Provider: **Jina Search** (`s.jina.ai`), reusing the existing `JINA_API_KEY`. Chosen
because it needs no new signup, no credit card, and stays within the project's
free-tier-forever rule — and we already run Jina for `fetch_url`'s fallback. Brave was
rejected (requires a card, bills past $5/mo). Google Custom Search (real Google results,
free 100/day, no card) is a viable alternative but needs GCP + a Programmable Search
Engine setup; it's deferred to a **future spec** if Jina's index proves insufficient.

Full design context: `docs/a2/trd.md` §4.3, `docs/specs/2026-08-25-analysis-agent-a2.md`.

---

## User Story

As the AnalystAgent, I want to search the web for a query so that I can find URLs and
context for an event when I don't already have a direct link.

---

## Acceptance Criteria

1. The agent can call `search_web(query)` and get back a ranked list of results
2. Each result carries `title`, `url`, `snippet`
3. A query with no results returns an empty list — not an error
4. API failures return a structured error the agent handles in-loop (mirrors `fetch_url`)

---

## Technical Design

### Tool schema

```yaml
name: search_web
description: Search the public web for a query. Returns ranked results to find URLs to fetch.
input_schema:
  query: string
returns:
  on success: [ { title: string, url: string, snippet: string }, ... ]   # top 5, ranked
  on no results: []
  on failure: { "error": "<status or reason>" }
```

### Provider — Jina Search (`s.jina.ai`)

```yaml
method: GET
endpoint: https://s.jina.ai/
query_params:
  q: <query>
headers:
  Authorization: "Bearer $JINA_API_KEY"
  Accept: application/json
  X-Respond-With: no-content     # results only (title/url/snippet), skip full page bodies
parse:
  from: data[]
  map: { title: item.title, url: item.url, snippet: item.description }
  take: first 5
```

`X-Respond-With: no-content` is load-bearing: by default Jina Search returns the full
readable text of each result, which would bloat the messages array. We want links and
snippets only — the agent uses `fetch_url` to pull a body once it picks a result. So
`search_web` never returns page bodies itself. (Exact header/field names verified against
the live API at build time.)

### Failure handling (consistent with `fetch_url`)

- Non-200 (401 bad/expired key, 5xx) → `{"error": "<status>"}`; the agent notes it and continues
- **Free-tier exhausted** (402 / 429) → `{"error": "search quota exceeded"}`; the agent
  continues without web results
- Empty `data` → return `[]` (a valid "nothing found," not a failure)

### Where it lives

A `search_web(query)` function alongside the other tools (`agent/analyst/`), registered
in the Claude tool-loop when the engine (AGE-95) exists. No coupling to Discord or Neon.

### Environment variable

| Variable | Purpose |
|---|---|
| `JINA_API_KEY` | Jina API token — **already set in `.env`** (shared with `fetch_url`'s fallback) |

---

## Behavioral Specs (Gherkin)

```gherkin
Scenario: Query returns results
  Given JINA_API_KEY is set
  When the agent calls search_web("CalOptima Covered California 2027")
  Then Jina returns search results
  And the tool returns a list of {title, url, snippet}, at most 5 items, in rank order
  And no result includes full page body text

Scenario: Query returns nothing
  Given a query Jina has no results for
  When the agent calls search_web(query)
  Then the tool returns an empty list
  And the agent treats it as "nothing found," not an error

Scenario: API key is rejected
  Given JINA_API_KEY is missing or invalid
  When the agent calls search_web(query)
  Then Jina responds 401
  And the tool returns {"error": "401 ..."} and the agent continues

Scenario: Free tier exhausted
  Given the Jina free-tier token budget is used up
  When Jina responds 402 or 429
  Then the tool returns {"error": "search quota exceeded"}
  And the agent continues the analysis without web results
```

---

## Test Plan

Pure-testable (failing-test-first, real pytest, mocked HTTP):
- Parse a sample Jina JSON body → list of `{title, url, snippet}`, capped at 5, no body text
- Empty `data` → `[]`
- Non-200 response → `{"error": ...}` (no exception raised to the agent)

Manual/integration:
- One live query against Jina with the real key returns sensible results

---

## Decisions

| Question | Decision | Rationale |
|---|---|---|
| Provider | Jina Search (`s.jina.ai`) | Free tier, no card, reuses existing `JINA_API_KEY`; stays free-tier-forever |
| Provider rejected | Brave Search API | Requires a credit card and bills past $5/mo credits |
| Provider deferred | Google Custom Search JSON API | Real Google results, free 100/day no card, but needs GCP + Programmable Search Engine setup — future spec if Jina's index falls short |
| Result count | Top 5 | Enough to pick a URL; keeps tool output small in the messages array |
| Fields returned | `title`, `url`, `snippet` (no page body) | The minimum the agent needs to choose what to fetch; `fetch_url` pulls bodies |
| Failure behavior | Structured `{"error": ...}`, agent handles in-loop | Consistent with `fetch_url`; no special-case code |
| Fetching page bodies | Not here — that's `fetch_url`'s job | Keep tools single-purpose; avoid bloating the messages array |

---

## Out of Scope

- Google Custom Search provider — candidate **future spec**, not this one
- `search_articles` (local article DB search) — a separate tool, specced later
- News / image / video search verticals — web results only
- Result caching, re-ranking, or dedup — return Jina's order as-is
- Pagination beyond the top 5

---

## Libraries

| Library | Version | Purpose |
|---|---|---|
| `requests` | current installed | Jina Search HTTP call |

**Prerequisite:** none — `JINA_API_KEY` is already in `.env`.
