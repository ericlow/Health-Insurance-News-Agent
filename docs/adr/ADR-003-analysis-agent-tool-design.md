# ADR-003: Analysis Agent (A2) Tool Design

**Date:** 2026-08-23
**Status:** Accepted

---

## Context

The A2 analysis agent needs to pull primary data across multiple health insurance programs (ACA individual, Medicaid managed care, Medicare Advantage, commercial) in 7 target states (CA, NV, CO, MO, WI, NY, NJ). The first design produced program-specific wrapper tools — `get_enrollment_by_region`, `get_sb260_default_carrier`, `get_ra_transfers` — one per known dataset.

The SB 260 incident (AGE-71 rev 1–2) established a second requirement: the agent must consult a curated knowledge base of standing regulatory mechanisms before touching any data, because those mechanisms (a 2019 California statute) generate no headlines and appear in no dataset — they are simply invisible to a data-only retrieval strategy.

---

## Decision

**Five tools. No program-specific wrappers.**

| Tool | Phase | Purpose |
|---|---|---|
| `search_articles(query)` | Research | Search local article DB (14 newsroom sources) for context on entities/event |
| `fetch_page(url)` | Research | Fetch specific URLs — press releases, trade press, announcements |
| `lookup_regulatory_rules(context)` | Rules | Mandatory first step; returns mechanisms + dataset pointers for the relevant member flow |
| `download_and_parse(url)` | Data | Downloads and parses any XLSX/PDF; produces HIGH-confidence claims |
| `post_to_discord(channel, message)` | Output | Posts structured findings back to Discord where Matt triggered the request |

`lookup_regulatory_rules` runs before any data pull — not as a suggestion but as a forced first step in the agent's system prompt.

---

## Options Considered

### Program-specific wrappers (rejected)

The initial design had a dedicated tool per dataset: `get_enrollment_by_region` (Covered CA XLSX), `get_sb260_default_carrier` (SB-260 PDF), `get_ra_transfers` (CMS Appendix C), and equivalent tools for Medicare Advantage. This approach was rejected for two reasons:

1. **YAGNI.** 7 states × 4 programs = ~28 dataset locations. Each new state or program requires new code shipped to production. The scope is finite and enumerable — it belongs in configuration, not in code.

2. **Wrong abstraction.** The agent doesn't need to know it's in a Covered CA analysis vs. an MA analysis. It needs to know which URL to fetch for the program it's looking at. That routing logic belongs in the rules layer, not in a tool's function signature.

### Generic downloader + rules layer (chosen)

`download_and_parse(url)` handles any structured file regardless of program or state. The rules layer (`docs/regulatory-rules.md`) encodes the routing: which mechanisms apply to a given member flow, and which dataset URLs contain the relevant current-state data. Adding a new state or program means updating a markdown file — no code change.

---

## Consequences

- **Rules layer is dual-purpose.** `lookup_regulatory_rules` must return two things: (1) the regulatory mechanism in plain language (SB 260 auto-enrolls Medi-Cal leavers into the county's lowest-cost Silver plan), and (2) the dataset pointer (the relevant file is at [URL]). If it only returns the mechanism, the agent still doesn't know what to download.

- **Matt maintains the rules layer.** The rules layer is only as good as what domain expertise went into it. Matt seeds it; updates require his review. This is intentional — the SB 260 miss happened because a 2019 statute wasn't in scope. Matt would have caught it immediately.

- **HIGH-confidence claims require `download_and_parse`.** Web-fetched content (from `fetch_page` or `search_articles`) is MEDIUM confidence at best. Scenario outputs are LOW by construction. The confidence floor for actionable claims is HIGH, which means a file was downloaded and parsed directly.

- **`search_web` deferred.** A general web search tool was considered for the research phase but deferred — `search_articles` (local DB) + `fetch_page` (known URLs from rules layer) covers the immediate need. Add when a real gap is demonstrated.
