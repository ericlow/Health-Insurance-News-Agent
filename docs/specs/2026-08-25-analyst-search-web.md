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

Provider decided as **Brave Search API** (see Decisions; matches TRD §4.3).

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

### Provider — Brave Search API

```yaml
method: GET
endpoint: https://api.search.brave.com/res/v1/web/search
query_params:
  q: <query>
  count: 5
headers:
  X-Subscription-Token: $BRAVE_API_KEY
  Accept: application/json
parse:
  from: web.results[]
  map: { title: result.title, url: result.url, snippet: result.description }
```

Return the top 5 results. The agent reads titles/snippets, picks the relevant URL(s),
and calls `fetch_url` on them — so `search_web` never fetches page bodies itself.

### Failure handling (consistent with `fetch_url`)

- Non-200 (401 bad key, 5xx) → `{"error": "<status>"}`; the agent notes it and continues
- **429 rate limit** → retry with backoff, then return the error if still failing.
  Brave's free tier is ~1 request/second — the wrapper must not burst
- Empty `web.results` → return `[]` (a valid "nothing found," not a failure)

### Where it lives

A `search_web(query)` function alongside the other tools (`agent/analyst/`), registered
in the Claude tool-loop when the engine (AGE-95) exists. No coupling to Discord or Neon.

### Environment variable

| Variable | Purpose |
|---|---|
| `BRAVE_API_KEY` | Brave Search API subscription token |

---

## Behavioral Specs (Gherkin)

```gherkin
Scenario: Query returns results
  Given BRAVE_API_KEY is set
  When the agent calls search_web("CalOptima Covered California 2027")
  Then Brave returns web results
  And the tool returns a list of {title, url, snippet}, at most 5 items, in rank order

Scenario: Query returns nothing
  Given a query Brave has no results for
  When the agent calls search_web(query)
  Then the tool returns an empty list
  And the agent treats it as "nothing found," not an error

Scenario: API key is rejected
  Given BRAVE_API_KEY is missing or invalid
  When the agent calls search_web(query)
  Then Brave responds 401
  And the tool returns {"error": "401 ..."} and the agent continues

Scenario: Rate limited
  Given the free-tier rate limit is hit
  When Brave responds 429
  Then the tool retries with backoff
  And returns results if a retry succeeds, else {"error": "429 ..."}
```

---

## Test Plan

Pure-testable (failing-test-first, real pytest, mocked HTTP):
- Parse a sample Brave JSON body → list of `{title, url, snippet}`, capped at 5
- Empty `web.results` → `[]`
- Non-200 response → `{"error": ...}` (no exception raised to the agent)

Manual/integration:
- One live query against Brave with a real key returns sensible results

---

## Decisions

| Question | Decision | Rationale |
|---|---|---|
| Provider | Brave Search API | Simple REST, one key, free tier (~2k/mo), independent index; TRD's pick |
| Result count | Top 5 | Enough to pick a URL; keeps tool output small in the messages array |
| Fields returned | `title`, `url`, `snippet` | The minimum the agent needs to choose what to fetch |
| Failure behavior | Structured `{"error": ...}`, agent handles in-loop | Consistent with `fetch_url`; no special-case code |
| Rate limiting | Retry on 429 with backoff; respect ~1 req/s free-tier limit | Avoid bursting the free tier into hard failures |
| Fetching page bodies | Not here — that's `fetch_url`'s job | Keep tools single-purpose |

---

## Out of Scope

- `search_articles` (local article DB search) — a separate tool, specced later
- News / image / video search verticals — web results only
- Result caching, re-ranking, or dedup — return Brave's order as-is
- Pagination beyond the top 5

---

## Libraries

| Library | Version | Purpose |
|---|---|---|
| `requests` | current installed | Brave API HTTP call |

**Prerequisite:** a `BRAVE_API_KEY` from Brave Search API signup (https://brave.com/search/api/).
