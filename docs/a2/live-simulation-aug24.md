# Live Simulation — CalOptima OC Entry (Aug 24, 2026)

A live run of the A2 agent design using real tools against real data, triggered by the same CalOptima article that produced the original AGE-71 Discord conversation. Goal: validate the design before writing the spec.

---

## What We Did

Simulated A2 agent execution using the actual tool set — `lookup_regulatory_rules`, `search_web`, `browse`, `search_articles` — against live web sources and real datasets. No mocked data.

**Tool call sequence:**

1. `lookup_regulatory_rules()` — returned full `docs/regulatory-rules.md`; SB 260, alternate-default, benchmark Silver mechanics, Medi-Cal COHS, RA program all surfaced immediately
2. `search_articles("CalOptima Orange County Covered California 2027")` — 0 results; A1 has not indexed CalOptima newsroom
3. `browse(Becker's URL)` — **403 blocked**
4. `search_web("CalOptima Covered California 2027 Orange County ACA entry")` — found CalOptima press release, Covered CA 2027 rate announcement
5. `browse(CalOptima press release)` — confirmed lowest-cost Silver OC PY2027, 15k Medi-Cal pipeline target
6. `search_web("Covered CA SB-260 Lowest Cost Silver by County 2026 PDF")` — found direct PDF URL
7. `browse(SB-260 PDF, extract="Orange County")` — confirmed **Anthem holds OC 2026 default slot**
8. `search_web("Covered CA Active Member Profile 2026 XLSX")` — found enrollment file URL
9. `browse(XLSX URL)` — **binary content returned; required Bash + pandas fallback** (see design finding below)
10. Parsed XLSX locally → extracted Region 18 carrier breakdown

---

## Domain Findings

**Region 18 (Orange County) — Covered CA, March 2026 [HIGH — Covered CA Active Member Profile XLSX]**

| Carrier | Members | Share |
|---|---|---|
| Blue Shield of California | 55,360 | 32.4% |
| Anthem Blue Cross | 52,950 | 31.0% |
| Kaiser Permanente | 51,930 | 30.4% |
| Health Net | 9,790 | 5.7% |
| Molina Healthcare | 770 | 0.5% — exiting PY2027 |
| **Total** | **170,790** | |

Silver tier (all CSR bands): **102,090 members (59.8% of OC market)**

**SB 260 status [HIGH — Covered CA SB-260 county table]:** Anthem holds OC default slot for PY2026.

**CalOptima entry [MED — CalOptima press release]:** Lowest-cost Silver OC PY2027. 15k Medi-Cal pipeline target. Default transfers by statute Nov 1, 2026.

**OC rate environment [MED — Covered CA]:** 10.4% rate increase in OC for PY2027 while CalOptima enters below benchmark. Gap is widening in real time.

**Anthem modeled exposure [LOW]:**
- Direct Silver switching: ~1,000–1,600 members
- Forgone SB 260 inflow: ~2,500–3,000 members/year (acquisition channel closes entirely)
- **Combined: ~3,500–4,800 members / ~$34–47M gross premium**
- Base case: ~4,000 members / ~$39M
- RA partial offset: ~$3–4M/year reduction in CA pool payment

These numbers confirm the scenario doc (AGE-71 scenario: 3,850–4,250 members / $38–42M). Real data validated the analysis direction.

---

## Three Domain Findings the Scenario Doc Missed

These surfaced from real data and weren't in the pre-written scenario.

**1. Silver concentration is 59.8% of the entire OC market — not just Anthem's book.**
The estimate in the regulatory-rules doc ("Anthem's OC book is approximately 71% Silver") referred to Anthem specifically. The whole market is nearly 60% Silver. The benchmark reset hits 102,090 members across all carriers simultaneously, not just Anthem's subsidized book.

**2. The alternate-default pathway is stronger than the primary default.**
CalOptima is OC's COHS — every Medi-Cal leaver already has a CalOptima relationship. Under SB 260, the alternate-default (existing Medi-Cal plan offering a Covered CA product in the county) takes statutory precedence over the price-based default. Anthem loses the SB 260 acquisition channel regardless of whether CalOptima has the absolute lowest premium. The COHS relationship makes this double-locked.

**3. The OC rate environment actively widens the exposure.**
OC rates increasing 10.4% in 2027 while CalOptima enters below benchmark. The net premium gap for Anthem's subsidized Silver members grows before anyone actively switches. By the time members shop in November, the incentive to move is larger than it appears today.

---

## Agent Design Learnings

### What worked as designed

**`lookup_regulatory_rules()` as mandatory first call.** SB 260 surfaced immediately, including the alternate-default pathway — the piece most likely to be missed. The structural fix (forced first call before any data pull) prevented the AGE-71 class of miss without requiring any special logic. The rules layer also pointed to the exact right datasets: Covered CA XLSX, SB-260 county table, CMS RA report.

**Multi-step data navigation.** The real path from "CalOptima entering OC" to "Anthem 52,950 members, 31%": web search → CalOptima press release → SB-260 PDF → Covered CA data portal → XLSX download. Never a direct URL. The design assumed this would be the normal case; the simulation confirmed it.

**Failure pivot on `browse` returning 403.** Becker's blocked immediately. The agent pivoted to the CalOptima press release and Covered CA announcement without surfacing this as a blocker — the correct behavior since Becker's was not the only source. The structured error path worked.

**Rules layer evidence guidance is directional, not literal.** The rules doc says "search coveredca.gov for SB-260 Lowest Cost Silver Plan by County." We found the exact PDF via `search_web`. The evidence hints were accurate enough to navigate to current data; they don't need to be permanent URLs to be useful.

### One confirmed design gap: XLSX parsing in `browse`

**The most important finding.** When `browse` fetched the Covered CA XLSX, the tool returned binary content — unparseable without a local fallback to Bash + pandas. The enrollment file is the single highest-confidence data source for this analysis (170,790 members, carrier breakdown, metal tier mix). Without proper XLSX parsing in `browse`, that data is unreachable.

This is not a nice-to-have. HIGH-confidence claims require parsed structured files. Without XLSX support in `browse`, the agent can only reach MED-confidence data (web pages), which corrupts the confidence tagging system — the agent would have to report Anthem's member count as MED when the actual figure is available in a machine-readable file.

**Spec must define:** `browse` XLSX/CSV handling is a build requirement, not an enhancement. The `extract` param is also load-bearing: the Region sheet is 317 rows × 42 columns. Returning everything every turn would be expensive; filtering to Region 18 before returning is the right behavior.

### The `extract` param justification

Confirmed in practice. A real enrollment file is not a small table. The `extract` param (filter rows/sections matching a keyword before returning) keeps tool output bounded without AI summarization. Without it: either the agent returns a 49KB table into the messages array (expensive across multi-turn), or the file gets summarized (corrupts figures). Filtering verbatim is the right path.

### What the simulation did NOT exercise

**Interruption/resume contract.** Every data source was publicly reachable; no blocker question was posted to Discord, no Lambda B termination was needed. The SCAN/Costco case ("two unnamed states") would test this path — the agent would need to post a question and terminate, then resume from history when Matt replies.

**Article DB search.** `search_articles` returned 0 results because CalOptima's newsroom isn't in A1's 14 sources. This is a coverage gap worth noting, not a design flaw, but it shows that `search_web` is load-bearing even when A1 runs correctly. The newsroom monitor list should eventually include health plan newsrooms that are also Covered CA participants.

---

## Conclusions for the Spec

1. **`browse` XLSX/CSV support is a build requirement.** Define it in the spec as a first-class content type, not an enhancement.

2. **`extract` param is required, not optional.** Document behavior: keyword filter returns verbatim matching rows; no AI summarization at any point.

3. **`search_web` is load-bearing, confirmed.** 4 of 10 sources in this run were found via web search. Design validated.

4. **The rules layer → `search_web` → `browse` chain is the normal data path.** No source was reached by direct URL. Spec should reflect this as the standard flow, not an edge case.

5. **Alternate-default pathway belongs in the rules layer, not the scenario doc.** The COHS alternate-default mechanic was in `regulatory-rules.md` and was surfaced automatically. It would have been missed in a data-only run. This validates Matt's role in seeding the rules layer.

6. **Becker's is solvable via Jina Reader.** The live run hit a 403 on Becker's. Jina Reader (`r.jina.ai/url`) with an API key retrieved the full article cleanly — title, publish date, clean markdown body. Confirmed Aug 24, 2026. Jina belongs in `browse`'s 403 retry chain before Wayback Machine. Free tier (10M tokens, ~3 years at A2's volume). `JINA_API_KEY` stored in `.env`. The spec should define the full retry chain in `browse`'s failure path; Becker's-class 403s should be invisible to the agent.
