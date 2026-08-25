# A2 Design Discussion — Aug 24, 2026

This document captures the full implementation design conversation for the A2 analysis agent. PRD, TRD, and ADR-003 are already written — this session drilled into the *how* before writing the spec.

---

## All Confirmed Decisions

### 1. Command: `/analysis`

Single Discord slash command. Matt uses it for new analyses, continuations, and search — the system determines intent from the input.

**Three behaviors from one command:**

| Input shape | Behavior |
|---|---|
| `/analysis <url> <question>` | New analysis — URL detected |
| `/analysis <nickname> <message>` | Continuation — exact nickname match in Neon |
| `/analysis <free text>` | Fuzzy search — vector similarity against past conversations |

### 2. Two-Lambda execution pattern

Discord requires a response within 3 seconds. Analysis takes minutes.

- **Lambda A (ack handler):** receives `/analysis` from Discord via API Gateway, immediately responds `{type: 5}` (deferred — shows "thinking..." spinner), generates nickname, invokes Lambda B asynchronously
- **Lambda B (analysis worker):** runs the full research + analysis loop (Claude + tools), posts findings to Discord via the follow-up webhook URL (valid 15 minutes)

No persistent bot process. Lambda A is trivial — ack, nickname, hand off.

### 3. Human-readable nicknames

Lambda A generates a memorable nickname from the URL slug at conversation creation. Matt never needs to remember a UUID.

**Generation logic** — from URL slug, strip stopwords, keep meaningful entities, join 2–3 terms:

- `look-inside-expanded-partnership-between-scan-and-costco` → **`scan-costco`**
- `caloptima-enters-orange-county-covered-california-market` → **`caloptima-oc`**
- `blue-shield-california-medi-cal-contract-loss` → **`blueshield-medicaid`**

Collision: append short date suffix — `scan-costco-aug24`.

Lambda A's immediate response to Matt:
> "Analysis started: **scan-costco**. I'll post findings here when ready."

### 4. Conversation identity: stable ID + thread as bonus

Each conversation has a stable `id` (primary key) and an optional `discord_thread_id`. Both resolve to the same conversation record via one lookup function.

The thread's value is visual containment — a natural home for the back-and-forth. It is not the identifier. Matt can continue from any context by nickname or vector search.

### 5. Interaction model: iterate then finalize

Matt submits article + question → agent responds → Matt corrects or adds context → repeat until satisfied → **finalize step** emits one clean consolidated artifact.

Working turns are deltas. The final artifact is a single structured analysis document, not a thread to scroll through.

**Finalize trigger:** still open — see below.

### 6. Storage: references, not payloads

- Articles go in the existing `articles` table (referenced by ID, not embedded in conversation)
- Tool results (fetched pages, parsed files) land in the messages array as part of conversation history — this IS the cache; no separate cache table needed
- Re-fetching every turn is unacceptable; tool results already present in messages are not re-fetched
- Constraint: free-tier-forever only — no S3, no AWS spend beyond what's already committed. Neon holds everything.

### 7. Caching reframe

The messages array is the cache. When the agent calls `fetch_page(url)` on turn 1, the result is in messages. On turn 4, the content is already there — no re-fetch. But the full messages array is re-sent to the Claude API every turn, which is why what's stored in tool results matters for cost.

### 8. Conversational model — core to v1

Not a future enhancement. The SCAN/Costco case proves it: "two unnamed states" — agent asks Matt, Matt answers, agent continues. Single-shot either blocks or guesses.

### 9. Vector search for conversation retrieval — confirmed v1

Matt retrieves past analyses without needing exact nickname recall. He types `/analysis costco medicare thing` and the system finds `scan-costco`.

**How it works:**
- At conversation creation, Lambda A embeds the article title + description using Voyage AI (`voyage-3-lite`)
- Embedding stored in Neon via `pgvector`
- On `/analysis <free text>` with no URL and no exact nickname match: embed the query → cosine similarity search → return top matches with nicknames + dates

**Embedding model:** Voyage AI `voyage-3-lite` (Anthropic's recommended provider) — 1024 dimensions, negligible cost at this volume.

**Schema:**

```sql
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE a2_conversations (
  id                TEXT PRIMARY KEY,
  nickname          TEXT UNIQUE NOT NULL,
  discord_thread_id TEXT UNIQUE,
  topic_embedding   vector(1024),
  topic_text        TEXT,              -- what was embedded, for debugging
  messages          JSONB NOT NULL,
  updated_at        TIMESTAMPTZ DEFAULT now()
);

-- similarity search index
CREATE INDEX ON a2_conversations
  USING ivfflat (topic_embedding vector_cosine_ops);
```

**Lookup function resolves any identifier to one conversation:**
1. Exact nickname match → return it
2. Discord thread_id match → return it
3. Vector similarity on free text → return top candidates, ask Matt to confirm

### 10. `lookup_regulatory_rules` — returns whole doc

Tool reads `docs/regulatory-rules.md` in full. No filtering. Agent reasons over it. Works while the doc is small (~5–10 mechanisms to start). Matt seeds and maintains it.

---

## What `docs/regulatory-rules.md` Is

Exists because of the SB 260 miss in AGE-71. A 2019 California statute generated no 2026 headlines and appeared in no dataset — invisible to any data-only strategy. Matt caught it immediately.

The rules layer is Matt's regulatory knowledge encoded as a document the agent reads before touching any data.

**Contents:** standing mechanisms governing member flows. Each entry returns:
1. **Mechanism** — rule in plain language + effect on member flows
2. **Dataset pointer** — which file, which URL, how often it updates

Examples:
- **SB 260 (CA ACA):** auto-enrolls Medi-Cal leavers into county's lowest-cost Silver plan; whoever holds default slot gets the inflow automatically
- **Benchmark Silver mechanics (ACA):** APTC pegs to second-lowest-cost Silver; new entrant undercutting benchmark shifts switching incentives market-wide
- **MA marketing rules:** CMS must approve before carrier can name states publicly; "two unnamed states" = filing pending, not secret
- **Medi-Cal continuous enrollment unwinding:** post-COVID eligibility wave feeding directly into SB 260 inflow

---

## Opus Design Review — Findings and Resolutions (Aug 24)

An independent Opus agent reviewed the design against all nine source documents, with focus on the data discovery and retrieval step. Three urgent issues identified and resolved.

### Finding: tool set was built on the happy path

The original 5-tool design (`search_articles`, `fetch_page`, `lookup_regulatory_rules`, `download_and_parse`, `post_to_discord`) modeled the one-third of AGE-71 sources that were direct file downloads. The other two-thirds — multi-step navigation, HTML-only data, blocked sources, Matt-provided files, mechanism-only — were unhandled.

### Resolution 1 — Matt provides files via URL or paste

When the agent cannot reach data (blocked, not public, behind a login), it asks Matt. Matt provides either a URL the agent can `browse`, or pastes the relevant content directly into his `/analysis` reply. Pasted content lands in message text and is immediately available to the agent.

Discord file attachments are out of scope — Matt shares data as a URL or paste.

### Resolution 2 — `search_web` un-deferred

`search_web` was deferred in ADR-003 as speculative. The Opus review established it is load-bearing: AGE-71 used web search for 4 of 12 sources, and Matt's stated method for a new event is "I'd start with a google search first." Cannot reproduce AGE-71 without it.

**Tool:** `search_web(query)` → returns top N results as `{title, url, snippet}`. Agent picks relevant URLs and calls `browse` on them.

**Provider:** Brave Search API. Confirmed.

### Resolution 3 — Interruption/resume contract

The conversational model is a sequence of interruptions. Lambda B cannot pause and wait for Matt. TRD Q3 ("how are partially-completed analyses recovered if interrupted?") was deferred — it cannot be.

**Contract:**
- Lambda B saves conversation state to Neon **after every significant turn**, not only at analysis completion
- When the agent hits a blocker it cannot resolve, it posts an explicit question to Discord and terminates cleanly — this is a checkpoint, not a failure
- Matt's reply triggers a new Lambda invocation; that Lambda loads full message history from Neon (all tool calls made, results received, findings so far, blocker question) and Claude resumes naturally — the history replay IS the resume
- No special resume logic needed in code; the messages array is the state

TRD Q3 is closed by this contract.

### Revised tool set — still 5 tools

| Tool | What it does |
|---|---|
| `search_articles(query)` | Searches the local article DB — 14 newsroom sources scraped by A1 — for prior coverage of the entities or events in the current analysis. Uses **vector similarity search** (Voyage AI `voyage-3-lite`, pgvector cosine similarity) against article embeddings stored in the articles table. Query string is embedded at search time. Returns top N articles by semantic relevance. **A1 pipeline impact:** articles must be embedded at insert time; existing articles require a one-time backfill. |
| `browse(url, extract=None)` | Fetches whatever is at a URL. Detects content type from the HTTP response and handles accordingly: HTML returns readable text plus all links; PDF returns extracted text; XLSX/CSV returns a structured table. If `extract` is provided, filters to matching rows or sections verbatim — never summarized. Returns `{content, content_type, url, status, suggested_confidence}`. On failure (403, login wall, stale URL, image-only PDF) returns a structured error with what was attempted. Replaces both `fetch_page` and `download_and_parse`. |
| `search_web(query)` | Searches the public web via Brave Search API. Returns top results as `{title, url, snippet}`. Used when the agent needs to find a URL it doesn't already have — navigating from a rules layer hint ("CMS publishes MA enrollment annually") to an actual current file. Un-deferred; load-bearing. |
| `lookup_regulatory_rules()` | Reads `docs/regulatory-rules.md` in full and returns it. No arguments, no filtering. Mandatory first call before any data pull. Tells the agent which standing regulatory mechanisms govern the relevant member flow, and where evidence for those mechanisms might be found. Prevents the SB 260 class of miss. |
| `post_to_discord(channel, message)` | Posts to the Discord thread where Matt triggered the analysis. Used for interim findings, blocker questions (checkpoint turns), and the final consolidated artifact. When posting a blocker question, Lambda B saves full conversation state to Neon and terminates — the next `/analysis` invocation resumes from that checkpoint. |

`fetch_page` and `download_and_parse` are retired. `search_web` replaces the deferral. Net count: 5.

**`browse` behavior:**
- Detects content type from HTTP response headers
- HTML → extracts readable text + all links; if `extract` param provided, filters to matching rows/sections verbatim (not summarized)
- PDF → extracts text layer; fails explicitly if scanned image with no text
- XLSX/CSV → returns structured table as text; if `extract` param provided, filters rows
- On failure (403, login wall, stale URL, timeout) → returns structured error with what was tried; agent records verification status and surfaces to Matt if needed
- Return value includes: `{content, content_type, url, status, suggested_confidence}`

### Additional findings — not yet resolved

See Opus review output for full detail. Lower priority but worth tracking:

- **Fetch-time summarization must not happen** — `browse` must return raw structured content for tables and files, never an AI summary of them. Paraphrased numbers corrupt MED-confidence claims.
- **Entity/region resolution has no home** — mapping county ↔ rating region ↔ HIOS ID ↔ dba names is load-bearing (AGE-71 mapped OC → Region 18). Goes in rules layer, system prompt, or a dedicated lookup. Needs a decision before build.
- **`browse` failure behavior** — 403s, login walls, year-stamped stale URLs, image-only PDFs. Defined above in `browse` behavior; needs implementation spec.

---

## Deferred — V2 Issues

### Context window management

Tool results (fetched pages, parsed XLSX data) live in the messages array and are re-sent to the Claude API on every subsequent turn. As analyses grow more complex — more files downloaded, longer conversations — cumulative tool result size inflates API cost and eventually risks pushing early context out.

**V2 fix:** selective pruning. After the agent processes a large tool result and extracts key facts into an assistant message, replace the raw tool result in the messages array with a compact summary before saving to Neon. The assistant message already contains the extracted facts; the raw data is no longer needed for reasoning.

Track as a known ceiling. Address when a complex analysis demonstrably hits cost or context limits.

---

## Still Open — Two Decisions Remaining

### A. `download_and_parse` — filter or full?

Large files (Covered CA XLSX, 1,000+ rows) cost tokens every subsequent turn because tool results re-send with messages. Options:

- **Full only:** return everything, agent extracts. Simple. Risk: expensive on large files across multi-turn conversations.
- **Optional query param:** `download_and_parse(url, query=None)` — if provided, filters rows by keyword before returning. Agent passes query when it knows what it's looking for (which it usually will, after `lookup_regulatory_rules` returns dataset pointers). If omitted, returns full.
- **Middle path (Eric's suggestion):** return full, then prune tool result to a summary after agent processes it. Requires splicing the messages array — non-trivial.

**Recommendation:** optional query param. One extra string arg, solves the problem cleanly, agent always knows context from the rules lookup.

**Not yet decided.**

### B. Finalize — slash command or natural language?

The finalize step emits one clean consolidated artifact at the end of iterative turns.

- **`/analysis finalize`** — explicit, predictable, Matt has to know the trigger word
- **Natural language** — "ok that looks good, write up the final" — agent detects intent, more natural; system prompt documents canonical triggers

**Recommendation:** natural language. Agent is Claude — intent detection is trivial. System prompt lists "finalize," "write it up," "that's good, publish" as triggers.

**Not yet decided.**

---

## What Happens After These Two Are Resolved

1. Update TRD (`docs/a2/trd.md`) — close §12 open questions, add implementation detail to body sections
2. Create ADR-004 — execution model: slash command + two-Lambda + Neon state + vector retrieval
3. Write the spec: `docs/specs/2026-08-25-analysis-agent-a2.md`

---

## Key Files for Context

- `docs/a2/prd.md` — what A2 is and why
- `docs/a2/trd.md` — two-phase workflow, five tools, confidence tagging, rules layer
- `docs/adr/ADR-003-analysis-agent-tool-design.md` — why generic tools, no program-specific wrappers
- `docs/adr/ADR-002-compute-platform.md` — why Lambda; conversational agents use stateless Lambda + Neon history
- `docs/analysis/age-71-caloptima-oc.md` — CalOptima analysis with §0 SB 260 post-mortem
