# AGE-71 — CalOptima's Covered California Entry: Elevance Member Impact and Risk Adjustment Analysis

**Date:** 2026-07-23 (rev. 2 — added per-claim citations, confidence levels, and source verification)
**Analyst:** Claude (Fable 5), for Eric Low
**Linear:** [AGE-71](https://linear.app/eric-projects/issue/AGE-71/caloptima-oc-entry-elevance-member-impact-and-risk-adjustment-analysis)

---

## How to read this report

Every factual claim carries a source tag `[S#]` and a confidence level:

- **HIGH** — read directly from a primary source file I downloaded and parsed myself (XLSX/PDF); numbers are exact.
- **MEDIUM** — from a fetched web page (AI-summarized during retrieval) or reputable secondary source; content believed accurate but not verified against a machine-readable primary.
- **LOW** — analyst estimate or judgment call; no external source exists. All scenario outputs are LOW by construction — they are models, not measurements.

Claims labeled **MECHANISM** are established ACA program rules (e.g., how APTC benchmarks work) stated from domain knowledge, not fetched for this report; they are textbook-verifiable.

## Analysis method

1. Pull the current Orange County (rating region 18) exchange market baseline — total enrollment, issuer shares, metal-tier mix — from Covered California's official enrollment file [S1].
2. Pull 2027 entry/exit facts (CalOptima entry, Molina exit, rate changes) from the Covered CA and CalOptima announcements [S4, S5, S6, S7].
3. Estimate CalOptima's year-1 gain as three additive components (Molina crosswalk defaults, Medi-Cal churn capture, incumbent switchers), each with low/base/high parameters. Capture-rate parameters are analyst judgment anchored to observed price-sensitivity evidence [S8].
4. Allocate incumbent-switcher losses to Anthem by its share of the contestable (non-Kaiser) Silver pool [S1], and value them at Anthem's average gross premium [S1].
5. Assess risk adjustment impact using CMS's final BY2024 issuer-level transfer data [S3] and pool-size data [S2], applied directionally to the projected member flows.

## Data sources and verification status

| ID | Source | Retrieval | Verification | Reliability |
|---|---|---|---|---|
| S1 | [Covered CA Active Member Profile, March 2026 (XLSX)](https://hbex.coveredca.com/data-research/library/CC_Membership_Profile_2026_03_R20260702.xlsx) | Downloaded, parsed with openpyxl | Region 18 issuer totals sum to sheet grand total (170,790); Molina R15+R18 = 1,600 matches press | **Primary — HIGH** |
| S2 | [CMS Summary Report, BY2024 RA transfers (PDF)](https://www.cms.gov/files/document/summary-report-individual-and-small-group-risk-adjustment-transfers-2024-benefit-year.pdf) | Downloaded, parsed with pypdf | Table 3 read directly | **Primary — HIGH** |
| S3 | [CMS Final BY2024 RA Appendix C, revised (XLSX)](https://www.cms.gov/files/document/final-by2024-appendixc-revised.xlsx-0) — issuer-level transfers | Downloaded, parsed with openpyxl | All 20 CA issuer rows read directly | **Primary — HIGH** |
| S4 | [Covered CA 2027 rates & plans release, 2026-07-21](https://www.coveredca.com/newsroom/news-releases/2026/07/21/covered-california-rates-and-plans-for-2027-california-continues-fight-for-health-insurance-affordability-and-access/) | WebFetch (AI-summarized) | Not independently verified | MEDIUM |
| S5 | [CalOptima press release — joining Covered California](https://www.caloptima.org/en/about-us/press-releases/caloptima-health-to-join-covered-california-as-an-affordable-plan-for-orange-county) | WebFetch (AI-summarized) | Not independently verified | MEDIUM |
| S6 | [Becker's Payer, 2026-07 — CalOptima only new ACA carrier](https://www.beckerspayer.com/payer/aca/caloptima-to-be-californias-only-new-aca-carrier-in-2027/) | Provided verbatim by Eric (docs/inputs.md) | Consistent with S4, S5 | MEDIUM |
| S7 | [ACA Signups — CA 2027 rate changes](https://acasignups.net/26/07/21/2027-rate-changes-california-99-indy-market) | WebFetch (AI-summarized) | Consistent with S4 | MEDIUM |
| S8 | [CalMatters, 2026-02 — plan-switching statistics](https://calmatters.org/health/2026/02/covered-california-health-bronze-plan/) | WebFetch (AI-summarized) | Quotes extracted directly | MEDIUM |
| S9 | DMHC 2024 RA Transfers Report ([FSSB Nov 2025 agenda item](https://www.dmhc.ca.gov/Portals/0/Docs/OFR/FSSB/Nov2025/AgendaItem8_2024RiskAdjustmentTransfersReport.pdf)) | **Bot-blocked (HTTP 403)** — figures seen only in search-index snippets | **Superseded**: all RA figures in this report now come from S3 instead | Not relied upon |

**Correction from rev. 1:** rev. 1 cited Anthem's CA individual RA payment as $438.8M from an unverified search snippet of S9. The CMS final revised figure [S3] is **$435,080,342**. All RA figures below are from S3.

---

## TL;DR

CalOptima Health enters Covered California in Region 18 (Orange County) for plan year 2027 as the lowest-cost Silver plan [S4, S5, S6 — MEDIUM]. **Base case (LOW confidence — modeled): CalOptima captures ~7,000 members in year 1 (~4% of the OC exchange market); Anthem loses ~1,100–1,500 members (~2–3% of its 52,950-member OC book [S1 — HIGH]), worth roughly $12–15M in annualized gross premium.** The larger strategic exposure is the benchmark reset: a cheaper Silver entrant raises net premiums for every incumbent's subsidized members [MECHANISM]. Risk adjustment impact is modestly *favorable* per-member for Anthem — Anthem paid $435.1M into the CA individual pool in BY2024 [S3 — HIGH], and losing healthy price-sensitive members shrinks that payment — but it offsets only ~25% of lost premium (LOW — modeled). The statewide pool barely moves: ~7k–13k new members vs. a pool of ~2.19M average members [S2 — HIGH]. **The issue's "individual/small group" framing should be corrected: this touches the individual pool only** (CalOptima's product is individual-market [S5 — MEDIUM]).

---

## 1. Market baseline (Region 18, March 2026) — all figures S1, HIGH confidence

**Total OC exchange enrollment: 170,790**

| Issuer | Members | Share |
|---|---|---|
| Blue Shield of California | 55,360 | 32.4% |
| **Anthem Blue Cross (Elevance)** | **52,950** | **31.0%** |
| Kaiser Permanente | 51,930 | 30.4% |
| Health Net | 9,790 | 5.7% |
| Molina Healthcare (exiting) | 770 | 0.5% |

**Metal tier mix (OC):** Silver tiers total 102,090 (59.8%) — base Silver 34,270; Enhanced 73 12,200; Enhanced 87 32,000; Enhanced 94 23,620. The Enhanced 87/94 population (55,620; 32.6% of market) is deeply subsidized and most price-reactive.

**Anthem statewide (exchange book, S1 — HIGH):** 169,500 members; metal mix 70.6% Silver (21.6% base + 48.9% CSR-enhanced); gross premium ~$823/member/month; ~22% of members pay $0 net premium; median net premium/policy $121.75.

**Derived (LOW — imputation):** Anthem's OC Silver membership ≈ 37,000, imputed by applying Anthem's *statewide* metal mix to its OC total, because Anthem's plan-level rows carry region "UNSPECIFIED" in S1 (verified data gap in the file, not an assumption I chose).

**Molina exit reconciliation (S1 — HIGH):** Molina has 830 members in region 15 and 770 in region 18; 830 + 770 = 1,600, exactly matching the "~1,600 displaced" in press reports [S6]. Of Molina's 770 OC members: 580 Silver, 120 Bronze, 40 Gold, 20 Platinum, 10 Minimum Coverage.

**2027 context:** 12 carriers statewide; statewide preliminary weighted average increase +9.9% [S4 — MEDIUM]; OC increase +10.4% [S7 — MEDIUM]. CalOptima is the only new entrant; entry is Region 18 only [S4, S6 — MEDIUM]. CalOptima positions as lowest-cost Silver, four metal tiers, network of 9,800 PCPs/specialists and 43 hospitals, and estimates "up to 15,000" OC residents transition off Medi-Cal annually [S5 — MEDIUM]. **Note:** the 15,000 is CalOptima's own statement of the *eligible churn pipeline*, not an enrollment projection — treated accordingly below.

---

## 2. Q1 — How many members does CalOptima gain?

**All scenario outputs: LOW confidence (modeled).** Parameters are analyst judgment; anchoring evidence cited per row.

| Component | Low | Base | High | Basis |
|---|---|---|---|---|
| (a) Molina crosswalk defaults | 350 | 550 | 750 | 770 OC Molina members [S1 — HIGH]; 580 Silver members default-map to lowest-cost same-tier carrier = CalOptima per stated crosswalk rule [S6 — MEDIUM]; 60–80% default-retention is analyst judgment (LOW) |
| (b) Medi-Cal churn capture | 1,500 | 4,000 | 7,500 | 10% / ~25% / 50% of the 15k annual pipeline [S5 — MEDIUM]; capture rates are analyst judgment (LOW); continuity-of-care + $0-premium Enhanced Silver eligibility for low-income churners supports meaningful capture [S4 — MEDIUM: ~200k Californians eligible for $0 Silver] |
| (c) Switchers from incumbents | 800 | 2,500 | 5,000 | 1% / 3% / 6% of ~83k contestable Silver pool (total Silver 102,090 minus Kaiser's 19,000 [S1 — HIGH]; excluding Kaiser is analyst judgment — integrated-model switching friction, LOW); price sensitivity anchor: 1 in 3 new enrollees chose cheapest tier for 2026, 130,000 renewers downgraded to Bronze statewide [S8 — MEDIUM] |
| **Total** | **~2,700** | **~7,000** | **~13,300** | **1.6% / ~4% / ~7.8% of the 170,790 OC market** |

Component (b) is largely **market expansion** (people who would otherwise churn to uninsured), not share taken from incumbents — only (a) and (c) come out of incumbent books (analyst reasoning — LOW).

Caps on the high case (analyst judgment — LOW): exchange consumers are not Medi-Cal members; CalOptima's Medi-Cal-centric network and zero commercial brand history may deter buyers despite its reach (819,000 Medi-Cal members, ~1 in 4 OC residents [S5 — MEDIUM]).

---

## 3. Q2 — How many members does Elevance/Anthem lose?

**All scenario outputs: LOW confidence (modeled).**

Allocation method: Anthem holds ~45% of the contestable non-Kaiser Silver pool (~37,000 of ~83,000 — the 37k is imputed, see §1), so it absorbs ~45% of component (c) plus none of (a) (Molina defaults route to CalOptima) and a small share of forgone (b) growth.

| Scenario | Anthem member loss | Annualized gross premium at $823 PMPM [S1 — HIGH] |
|---|---|---|
| Low | ~400 | ~$4M |
| **Base** | **~1,100–1,500** | **~$12–15M** |
| High | ~2,300–3,300 | ~$23–33M |

Base case is ~2–3% of Anthem's OC book — real but not structural (analyst judgment — LOW).

**The bigger exposure is the benchmark reset [MECHANISM + LOW for magnitude].** APTC subsidies peg to the second-lowest-cost Silver plan in a rating region (established ACA rule). If CalOptima prices below the current floor, the benchmark can drop, raising *net* premiums for subsidized members of every incumbent even at flat gross rates — compounding OC's +10.4% gross increase [S7 — MEDIUM]. With ~48.9% of Anthem's book in CSR-enhanced Silver [S1 — HIGH], this drives attrition beyond direct switching (downgrades to Bronze or exits — consistent with the 130k statewide downgrade wave [S8 — MEDIUM]). **The CalOptima-vs-benchmark price gap is not yet public; final 2027 rates publish in fall 2026. This is the single most important number to re-check (target: October 2026).**

Middle-income risk note: 22% of 224,000 middle-income (>400% FPL) enrollees statewide cancelled for 2026 after enhanced federal subsidies ended, and new middle-income sign-ups fell 59% [S8 — MEDIUM]. Anthem's unsubsidized OC members are already attriting for reasons unrelated to CalOptima — beware attributing all 2027 OC losses to the new entrant.

---

## 4. Q3 — Risk adjustment impact

**Baseline facts (S3 — HIGH, CMS final BY2024, CA individual market, exact figures):**

| Issuer | Individual-market RA transfer |
|---|---|
| Blue Shield of California | **+$1,330,103,054** (dominant receiver) |
| Anthem Blue Cross (DMHC) | **−$435,080,342** (payer) |
| Kaiser Foundation Health Plan | −$306,006,293 (payer) |
| L.A. Care | −$348,471,036 (payer) |
| Molina Healthcare of CA | −$75,929,574 (payer) |
| Health Net of California | −$17,300,891 (payer) |

Pool size: CA individual market = 26,304,962 billable member months ≈ **2.19M average members**; statewide average premium $563.23/month [S2 — HIGH].

**Effects of CalOptima's entry (directional analysis — LOW unless noted):**

1. **Anthem's transfer payment shrinks (favorable).** Anthem pays into the pool because its book codes healthier than market average [S3 — HIGH; interpretation MECHANISM]. Members lost to a lowest-cost Silver entrant skew healthy/low-coded (MECHANISM — price-sensitive switchers are systematically healthier). Rough magnitude: Anthem's payment ÷ its exchange membership ≈ $435.1M / 169,500 ≈ $2,570/member/year as an **upper bound** (true denominator includes Anthem's off-exchange individual book, which S3 does not break out — flagged, LOW). Base-case 1,100–1,500 lost members → RA payment relief roughly **$3–4M/year, offsetting ~25% of lost premium** (LOW — modeled). Net margin damage is modest: low-claims members carrying an RA charge are the cheapest members to lose.
2. **Molina's exit has the same sign.** Molina was a $75.9M payer [S3 — HIGH] — its exiting book is also healthy-coded, so its 770 OC members arriving at CalOptima (or elsewhere) carry low risk scores (LOW — inference).
3. **CalOptima likely enters as a payer.** New entrants' enrollees carry thin diagnosis histories and low year-1 coded risk scores (MECHANISM), and the churn population skews income-volatile [S5 — MEDIUM]. Expect CalOptima to pay in initially, scores maturing years 2–3 (LOW).
4. **Pool-level distortion is negligible (HIGH confidence in the bound).** 7k–13k new members against a 2.19M-member pool [S2 — HIGH] is <0.6% — no meaningful change to transfer mechanics.

**Correction to the issue (HIGH):** California's individual and small group risk adjustment pools are computed separately [S2 — HIGH: CMS reports them as separate risk pools]. CalOptima Health Covered is an individual-market product [S5 — MEDIUM]. **The small group pool is unaffected.** AGE-71's description should be amended.

---

## 5. Assumptions register

| # | Assumption | Confidence | Sensitivity |
|---|---|---|---|
| A1 | CalOptima prices meaningfully (>$10/mo) below the next-lowest Silver | LOW (rate gap unpublished until fall 2026) | High — if the gap is trivial, components (a) retention and (c) collapse toward the low case |
| A2 | Anthem's OC metal mix ≈ its statewide mix | LOW (forced by S1 data gap) | Medium — shifts Anthem's share of the contestable pool |
| A3 | Churn-pipeline capture 10/25/50% | LOW (judgment; no precedent data found) | High — dominates Q1 base case |
| A4 | Kaiser members excluded from contestable pool | LOW (judgment) | Medium — including them raises incumbent-switcher totals but dilutes Anthem's share |
| A5 | Molina crosswalk defaults to lowest-cost same-tier | MEDIUM [S6] | Low — component is small |
| A6 | Anthem RA per-member uses exchange-only denominator | LOW (known upper bound) | Low — affects only the offset estimate |
| A7 | "15,000" is pipeline, not projection | MEDIUM [S5 wording: "up to 15,000 … who transition out of Medi-Cal annually"] | High — if it were a real projection, Q1 base doubles |

## 6. Known gaps

- **2027 rate gap (CalOptima vs. benchmark Silver)** — not yet public; re-run when final rates post (fall 2026).
- **Anthem's off-exchange CA individual membership** — would tighten the RA per-member figure.
- **OC-specific Medi-Cal churn volume** — no independent verification of CalOptima's 15k found; DHCS churn data not located in this pass.
- **DMHC report [S9]** — bot-blocked; if Eric can pull it manually, it would cross-check S3 (DMHC aggregates DMHC-licensed entities and may differ slightly from CMS HIOS-level rows).

---

## Postscript — what the A2 Analysis Agent would need to automate this (input to AGE-68)

1. **Structured data fetch + parse**: XLSX (Covered CA profile, CMS appendices) and PDF (CMS reports) — spreadsheet/PDF tooling, not just HTML scraping.
2. **Region/entity resolution**: "Orange County" → rating region 18 → correct column in a 44-column sheet; HIOS ID ↔ carrier-name mapping (e.g., "California Physicians' Service dba Blue Shield"). Alias tables in the DB.
3. **Bot-blocked source fallbacks**: DMHC returned 403 to all fetch attempts; the workflow recovered by finding the equivalent CMS primary. A2 needs source-equivalence knowledge and must record verification status per claim.
4. **Claim provenance model**: this report's per-claim `[S#, confidence]` tagging should be A2's native output format — every generated claim carries source ID + retrieval method + confidence.
5. **Scenario modeling**: parameterized low/base/high tables with an explicit assumptions register.
6. **Temporal follow-up**: schedule re-analysis on known future data releases (final 2027 rates, fall 2026).
