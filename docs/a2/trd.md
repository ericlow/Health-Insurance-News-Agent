# Technical Requirements Document — Analysis Agent (A2)

_Last updated: 2026-08-23_

---

## 1. Overview

A2 is a conversational LLM agent with a tool belt. It receives a trigger (article + question) from Matt via Discord, runs a two-phase workflow (research → analysis), and posts structured findings back to Discord. It is not a pipeline — it is a single agent that picks tools to solve the problem, guided by its system prompt.

See `docs/a2/prd.md` for goals, users, and scope.

---

## 2. Interaction Model

A2 is a **collaborative conversation**, not a single-shot function. The Discord thread is the workspace:

```
Matt:  [article URL or text] + "how does this affect Anthem?"
A2:    Research findings + any blockers surfaced as questions
Matt:  [optional: fills a gap, corrects an assumption, sharpens the question]
A2:    Continues with updated context
Matt:  [optional: additional steering]
A2:    Final structured findings
```

The agent surfaces unknown information as targeted questions to Matt rather than hard-stopping or making silent assumptions. Matt's replies are incorporated and the agent continues from where it was — it does not restart.

**Why conversational:** the SCAN/Costco article named "two states" without specifying them. A single-shot agent either blocks or guesses. A conversational agent asks Matt, who may know, and continues in parallel on what it can resolve independently.

---

## 3. Two-Phase Workflow

### Phase 1 — Research

Goal: understand the event well enough to know what data to pull.

The agent:
- Searches the local article DB for prior coverage of the entities involved
- Fetches the triggering article and any linked primary announcements
- Identifies: market segment (ACA / MA / Medicaid / commercial), geography (state, county, rating region)
- Surfaces any gaps that Matt would need to fill (e.g., unnamed states, unconfirmed plan details)

This phase replicates how Matt said he approaches a new event: "google news and try to understand the situation" before pulling any structured data.

### Phase 2 — Analysis

Goal: answer Matt's question with primary data and confidence-tagged claims.

The agent:
1. Calls `lookup_regulatory_rules` first — mandatory, before any data pull
2. Pulls enrollment and financial datasets identified by the rules lookup
3. Models member flows and dollar exposure
4. Tags every claim HIGH / MED / LOW
5. Posts structured findings to Discord

---

## 4. Tools

The agent has exactly five tools. No program-specific wrappers — see ADR-003.

| Tool | Phase | What it does |
|---|---|---|
| `search_articles(query)` | Research | Searches the local article DB — 14 newsroom sources scraped by A1 — for prior coverage of the entities or events in the current analysis |
| `search_web(query)` | Research | Searches the public web via Brave Search API; returns top results as `{title, url, snippet}`; used to find URLs when the rules layer provides a hint but not a direct link |
| `browse(url, extract=None)` | Research / Analysis | Fetches whatever is at a URL; detects content type (HTML/PDF/XLSX/CSV) and returns raw content; optional `extract` param filters to matching rows or sections verbatim; returns `{content, content_type, url, status, suggested_confidence}` |
| `lookup_regulatory_rules()` | Analysis | Reads `docs/regulatory-rules.md` in full; mandatory first call before any data pull; returns standing regulatory mechanisms governing the member flow and where evidence might be found |
| `post_to_discord(channel, message)` | Output | Posts structured findings to the Discord thread; when posting a blocker question, Lambda B saves conversation state to Neon and terminates cleanly |

### 4.1 `lookup_regulatory_rules`

This tool is not optional. The system prompt instructs the agent to call it before any data pull.

It returns the full content of `docs/regulatory-rules.md` — no arguments, no filtering. The agent reasons over the full document. Each entry contains:

1. **Mechanism description** — the standing regulatory rule in plain language and its effect on member flows
2. **Evidence guidance** — where evidence for this mechanism might be found; this is a starting point for `search_web` + `browse`, not a guaranteed direct URL

Dataset filenames often embed year numbers (`_2026.xlsx`) that go stale. The rules layer records where to look, not a permanent link. `search_web` finds the current file.

**Why mandatory:** AGE-71 revisions 1–2 missed SB 260 entirely because no step asked "which standing rules govern this member flow?" A 2019 statute generates no 2026 headlines and appears in no dataset. Making `lookup_regulatory_rules` a forced first step structurally prevents this class of miss. See ADR-003 and `docs/analysis/age-71-caloptima-oc.md` §0.

### 4.2 `browse(url, extract=None)`

The primary data retrieval tool. Handles any URL regardless of content type — the agent does not need to know in advance whether a URL returns HTML, PDF, or a spreadsheet.

**Content-type dispatch:**
- HTML → readable text plus all links on the page (for navigation to find data files)
- PDF → extracted text layer; fails explicitly if the file is a scanned image with no text
- XLSX / CSV → structured table as text rows; `extract` param filters rows before returning

**`extract` parameter:** optional keyword filter. When provided, filters to rows or sections matching the terms before returning. Default is raw — never AI-summarized. Summaries corrupt exact figures. Load-bearing for large structured files (e.g. Covered CA enrollment XLSX is 317 rows × 42 columns; returning all of it into the messages array on every turn is prohibitively expensive).

**Return value:** `{content, content_type, url, status, suggested_confidence}`
- `status`: `ok` | `blocked` (403/login wall) | `stale` (404) | `unsupported` (scanned image)
- `suggested_confidence`: `HIGH` for parsed structured files; `MED` for fetched web pages

**403 retry chain:** when a URL returns 403, `browse` retries internally before returning a failure to the agent. The agent only sees success or a final structured failure after all methods are exhausted.

| Step | Method | Notes |
|---|---|---|
| 1 | Realistic User-Agent header | handles simple bot checks |
| 2 | Jina Reader (`r.jina.ai/url`) | handles JS-rendered pages and most Cloudflare; requires `JINA_API_KEY` env var; confirmed against Becker's Payer (Aug 2026) |
| 3 | Wayback Machine (`web.archive.org/web/*/url`) | handles most trade press; may be hours behind |
| 4 | Bing cache | last automated option |
| 5 | Structured failure | agent records gap and surfaces to Matt if data was needed |

**Jina API key:** free tier; 10M token limit (~3 years at A2's volume). Key stored in `JINA_API_KEY` env var. Must be rotated if leaked — do not log or commit.

Replaces both `fetch_page` and `download_and_parse` from earlier designs.

### 4.3 `search_web(query)`

Searches the public web via Brave Search API. Returns top N results as `{title, url, snippet}`.

Used when the agent needs a URL it doesn't already have — navigating from a rules layer evidence hint to the actual current file. Also used in the research phase to understand an event before pulling structured data.

This tool was deferred in an earlier design. It is un-deferred because the evidence establishes it as load-bearing: four of twelve sources in AGE-71 were found via web search, and Matt's stated first step on any new event is "I'd start with a google search."

### 4.4 `search_articles(query)`

Searches the local article DB — 14 newsroom sources scraped by A1 — for prior coverage of the entities or events in the current analysis. Called before hitting the web so the agent uses what A1 has already collected.

### 4.5 `post_to_discord(channel, message)`

Posts structured findings to the Discord thread where Matt triggered the analysis. Used for interim updates, blocker questions, and the final consolidated artifact.

**Checkpoint behavior:** when posting a blocker question, Lambda B saves the full conversation state (messages array) to Neon before terminating. Matt's reply triggers a new Lambda invocation; that Lambda loads full history from Neon and Claude resumes — the history replay is the resume mechanism. This is the defined contract for TRD Q3.

---

## 5. Confidence Tagging

Every factual claim in the output carries a confidence tag:

| Tag | Meaning |
|---|---|
| **HIGH** | Read directly from a primary source file downloaded and parsed by `download_and_parse`; numbers are exact |
| **MED** | From a fetched web page (`fetch_page`) or reputable secondary source; believed accurate but not verified against a machine-readable primary |
| **LOW** | Analyst estimate or model output; all scenario projections are LOW by construction |
| **MECHANISM** | Established program rule from the rules layer, verifiable in statute or regulation |

---

## 6. Rules Layer

`docs/regulatory-rules.md` is the agent's curated knowledge base of standing regulatory mechanisms. It is a markdown document, not code.

Structure per entry:
- Program and state
- Mechanism description
- Effect on member flows
- Dataset URLs (with update frequency)
- Relevant statutes or regulations

**Matt maintains this.** He seeds the initial content; updates require his review. The rules layer is only as good as the domain expertise in it.

Adding a new state or program to the rules layer requires no code change — only a document update.

---

## 7. Programs and Data Sources

The agent is scoped to 7 states (CA, NV, CO, MO, WI, NY, NJ) and 4 programs. The rules layer encodes the dataset URLs per program per state.

| Program | Primary enrollment data | Financial sizing |
|---|---|---|
| ACA individual | State exchange enrollment file (Covered CA XLSX for CA; CMS for federal exchange states) | CMS RA Appendix C (XLSX) |
| Medicaid managed care | CMS managed care enrollment report | State capitation rate schedules |
| Medicare Advantage | CMS MA Enrollment by Plan/County | CMS MA rate announcements |
| Commercial fully-insured | State DOI filings (less structured; lower confidence) | N/A |

---

## 8. System Prompt

The agent's system prompt encodes standing context so Matt doesn't repeat it per request:

- Perspective: always Elevance / Anthem Blue Cross
- Target states: CA, NV, CO, MO, WI, NY, NJ
- Default question framing: impact on Anthem's book (member count, dollar exposure)
- Mandatory first tool call: `lookup_regulatory_rules`
- Confidence tagging requirements
- Output format: structured Discord post with citations

---

## 9. Model

`claude-sonnet-4-6` (or best available Sonnet at build time). A2 runs infrequently and on-demand — cost per run is not a constraint. Quality is.

---

## 10. Test Cases

Two events with known ground truth to validate the agent against:

| Event | Market | Primary source | Known finding to verify |
|---|---|---|---|
| CalOptima entering OC Covered CA market (2027) | ACA individual, CA | `docs/AGE-71 — CalOptima OC Entry Analysis - Discord conversation.txt` | SB 260 default slot shifts to CalOptima; Anthem loses ~3,850–4,250 members combined switching + forgone inflow |
| SCAN / Costco co-branded MA partnership | Medicare Advantage | `docs/A look inside the expanded partnership between SCAN and Costco.txt` | States unnamed pending CMS filing; agent should surface this as a blocker and ask Matt |

---

## 11. What Is Deferred

| Item | Why deferred |
|---|---|
| Automated critic layer | Matt is the critic in v1; his judgment is more reliable than any automated layer we can build now |
| `search_web` tool | `search_articles` + `fetch_page` covers immediate need; add when gap is demonstrated |
| Pre-caching enrollment datasets | Fetch on demand first; add caching if latency becomes a problem |
| Discord bot invocation mechanism | Needs Discord bot integration work; define when that is built |
| Non-Anthem perspective | V1 always frames from Elevance's perspective; generalize when use case arises |

---

## 12. Open Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | How does the agent maintain conversational state between Matt's replies in Discord? | **Closed** — stateless Lambda + Neon messages array; each Lambda invocation loads full conversation history; slash command `/analysis <nickname>` in-thread routes to existing conversation |
| Q2 | Pre-cache vs. fetch on demand for enrollment datasets? | Deferred — fetch on demand; add caching if latency becomes a problem |
| Q3 | How are partially-completed analyses recovered if the agent is interrupted? | **Closed** — Lambda B saves messages array to Neon after every significant turn; blocker = explicit question posted to Discord + clean termination; Matt's reply triggers a new Lambda that loads history and resumes; see §4.5 |
