# Product Requirements Document — Health Insurance News Agent

_Last updated: 2026-06-20_

---

## 1. Problem Statement

Significant relationship changes between health insurers and providers — network exits, acquisitions, TPA shifts — are high-signal events for industry analysts, but they're hard to catch in real time. They surface across dozens of sources (carrier newsrooms, trade press, financial filings, government procurement announcements), often with leading indicators (soft RFPs, account team layoffs) appearing weeks before the public announcement.

An analyst monitoring this manually would need to read dozens of sources daily and know what early signals to look for. This system automates that monitoring and surfaces structured analysis when something significant happens.

---

## 2. User

**Primary user:** Eric (industry analyst)

Needs:
- Early warning of major carrier/provider relationship changes, ideally before they're publicly confirmed
- Enough context per story to understand the economic stakes and affected parties without having to do the research himself
- Awareness of leading indicators, not just confirmed announcements

Not needed:
- Coverage of small regional players or routine contract renewals
- Real-time feeds or sub-hourly latency

---

## 3. What We're Building

A hierarchical multi-agent pipeline that:

1. **Monitors** health insurance industry news sources on a schedule (every 8 hours)
2. **Flags** articles that signal a significant relationship change (or a leading indicator of one)
3. **Analyzes** each flagged story by spawning sub-agents that:
   - Define the geographic regions impacted
   - Estimate member count and revenue impact via LLM analysis of the article
   - Research alternatives available to affected parties
4. **Remembers** which articles have been processed so they are never re-flagged or re-analyzed

---

## 4. Relationship Types in Scope

| Type | Description | Example |
|------|-------------|---------|
| Network agreement change | Provider joins or exits an insurer's network | Sutter exits Blue Shield network |
| Acquisition / merger | Insurer buys insurer, or provider buys provider | Cigna acquires Humana |
| Divestiture / termination | Insurer drops major provider or vice versa | United drops CalPERS |
| TPA shift | Self-funded employer switches claims processor | CalPERS moves from United/Anthem to Sutter/Anthem |
| Provider-sponsored plan | Provider builds its own insurance product | Sutter launches its own health plan |

**Time frame:** Stories from the last 5 years are in scope. Recency within that window is preferred but not required.

---

## 5. Leading Indicators to Detect

These are pre-announcement signals the system should actively look for:

- **Soft RFP language** — large purchasers (CalPERS, large employers, unions) publicly signaling intent to switch carriers or put contracts out to bid
- **Account team layoffs** — a carrier laying off the sales/account team that serves a specific client, which historically precedes contract loss by weeks
- **Provider network expansion** — a provider system announcing its own plan or expanding into insurance, which signals it may be about to exit existing network agreements

---

## 6. Sources

**v1 (must-have):**

| Source | URL | Method |
|--------|-----|--------|
| Becker's Payer | beckerspayer.com | RSS feed (`/feed/`) |

**Future (not in v1):**

| Category | Examples |
|----------|---------|
| Carrier newsrooms | newsroom.cigna.com, newsroom.uhc.com, anthem.com/news |
| Trade press | Modern Healthcare, Health Affairs, Fierce Healthcare |
| Financial / general news | Yahoo Finance/Healthcare |
| Government / procurement | State insurance department filings, CalPERS board meeting minutes |

---

## 7. Output

When the system flags a story, the analyst receives a structured briefing containing:

- **What happened** (or what's signaled) — 2–3 sentence summary
- **Entities involved** — names, roles (insurer / provider / employer / TPA)
- **Geographic scope** — states or regions affected
- **Economic sizing** — LLM-estimated member count and revenue impact based on article content
- **Alternatives** — what options the affected parties have (e.g., which other carriers could absorb displaced members)
- **Source links** — original articles / filings

**Delivery:** Abstracted / TBD. The system will produce a structured briefing object; delivery mechanism (email, Slack, file) is not decided for v1.

---

## 8. Success Metrics

The system is working if:

1. It catches ≥80% of significant carrier/provider relationship changes within 48 hours of first public signal
2. False positive rate is low enough that Eric reads every alert (target: <20% of alerts are noise)
3. Each briefing saves Eric meaningful research time — he should not need to go find the economic sizing or alternatives himself

---

## 9. Out of Scope

- Small regional carriers or provider groups with no multi-state footprint
- Routine contract renewals without a change in parties or terms
- Medicare/Medicaid-specific regulatory changes (unless they trigger a network or TPA shift)
- Building a UI or dashboard (v1 delivers alerts in a simple structured format, delivery TBD)

---

## 10. Open Questions

| # | Question | Why it matters | Status |
|---|----------|----------------|--------|
| Q1 | How are alerts delivered to Eric? | Determines output architecture (email, Slack, file, etc.) | Deferred — delivery is abstracted for now |
| Q2 | What is the minimum member count or revenue impact that makes a story "significant"? | Determines whether the system filters low-stakes stories or surfaces everything it finds | Decided — see decisions log |

---

## 11. Decisions Log

| Date | Decision |
|------|----------|
| 2026-06-20 | Monitor runs every 8 hours |
| 2026-06-20 | v1 source: newsroom.cigna.com only |
| 2026-06-21 | Added beckerspayer.com as v1 source — RSS feed at /feed/ is open (no Cloudflare), returns full article HTML, no Playwright required |
| 2026-06-21 | Dropped newsroom.cigna.com from v1 — beckerspayer.com (trade press) is broader and more discovery-oriented; carrier newsrooms deferred to future |
| 2026-06-20 | System stores processed article URLs/IDs; will not re-flag or re-analyze already-processed articles |
| 2026-06-20 | Economic sizing (member count, revenue) is estimated by LLM analysis of article text — not looked up from external databases |
| 2026-06-20 | Alert delivery mechanism is abstracted for v1; system produces a structured briefing object |
| 2026-06-20 | Significance threshold: stories are flagged if LLM estimates ≥thousands of members affected OR ≥millions of dollars in revenue impact |
