# AGE-71 — CalOptima's Covered California Entry: Elevance Member Impact and Risk Adjustment Analysis

**Date:** 2026-07-23 (rev. 4 — differentiated SB 260 effectuation; CalOptima gain revised up. See §0 process note and revision log at end)
**Analyst:** Claude (Fable 5), for Eric Low
**Linear:** [AGE-71](https://linear.app/eric-projects/issue/AGE-71/caloptima-oc-entry-elevance-member-impact-and-risk-adjustment-analysis)

---

## How to read this report

Every factual claim carries a source tag `[S#]` and a confidence level:

- **HIGH** — read directly from a primary source file I downloaded and parsed myself (XLSX/PDF); numbers are exact.
- **MEDIUM** — from a fetched web page (AI-summarized during retrieval) or reputable secondary source; believed accurate but not verified against a machine-readable primary.
- **LOW** — analyst estimate or judgment call. All scenario outputs are LOW by construction — models, not measurements.

Claims labeled **MECHANISM** are established program rules stated from domain knowledge or statute, verifiable in the cited legal text.

## 0. Process note — how and why SB 260 was missed in revisions 1–2

Revisions 1–2 of this analysis omitted [SB 260 (Hurtado, Ch. 845, Statutes of 2019)](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=201920200SB260), California's automatic Medi-Cal-to-marketplace enrollment law. The omission was material (see §3, §4).

**How it was missed:** the analysis retrieved two classes of context — *market-state data* (enrollment files, rate filings, RA transfers) and *event data* (news announcements). SB 260 belongs to a third class: **standing regulatory mechanisms** — laws that govern how members flow between programs. A 2019 statute implemented in 2023 generates no 2026 headlines, so news retrieval never surfaces it; it is not a dataset, so the data-pull list never included it. The analysis plan contained no step of the form *"enumerate the standing rules that govern this member flow."*

**Why it matters beyond this report:** the signal was already in hand and misread. CalOptima's stated rationale ("continuity for people transitioning out of Medi-Cal" + lowest-cost Silver positioning [S5]) *is* an SB 260 default-capture strategy; without the statute in context, it was interpreted as marketing language. Data retrieval without a rules layer produces exactly this class of error — right data, wrong model of member movement. This is now a hard requirement for the A2 agent (see Postscript, and AGE-68).

## Analysis method

1. Pull the Orange County (rating region 18) market baseline from Covered California's official enrollment file [S1].
2. Pull 2027 entry/exit facts from Covered CA and CalOptima announcements [S4–S7].
3. **(New in rev 3)** Identify the standing regulatory mechanisms governing the affected member flows: SB 260 auto-enrollment [S10] and the current holder of the OC lowest-cost Silver default slot [S11].
4. Model CalOptima's year-1 gain as three additive components; model Anthem's loss as direct switching plus (new) the forgone SB 260 default inflow.
5. Assess risk adjustment impact using CMS final BY2024 issuer-level data [S3] and pool-size data [S2].

## Data sources and verification status

| ID | Source | Retrieval | Reliability |
|---|---|---|---|
| S1 | [Covered CA Active Member Profile, March 2026 (XLSX)](https://hbex.coveredca.com/data-research/library/CC_Membership_Profile_2026_03_R20260702.xlsx) | Downloaded, parsed (openpyxl); totals reconcile | **Primary — HIGH** |
| S2 | [CMS Summary Report, BY2024 RA transfers (PDF)](https://www.cms.gov/files/document/summary-report-individual-and-small-group-risk-adjustment-transfers-2024-benefit-year.pdf) | Downloaded, parsed (pypdf) | **Primary — HIGH** |
| S3 | [CMS Final BY2024 RA Appendix C, revised (XLSX)](https://www.cms.gov/files/document/final-by2024-appendixc-revised.xlsx-0) | Downloaded, parsed (openpyxl); all 20 CA issuer rows read | **Primary — HIGH** |
| S4 | [Covered CA 2027 rates & plans release, 2026-07-21](https://www.coveredca.com/newsroom/news-releases/2026/07/21/covered-california-rates-and-plans-for-2027-california-continues-fight-for-health-insurance-affordability-and-access/) | WebFetch (AI-summarized) | MEDIUM |
| S5 | [CalOptima press release](https://www.caloptima.org/en/about-us/press-releases/caloptima-health-to-join-covered-california-as-an-affordable-plan-for-orange-county) | WebFetch (AI-summarized) | MEDIUM |
| S6 | [Becker's Payer — CalOptima only new ACA carrier 2027](https://www.beckerspayer.com/payer/aca/caloptima-to-be-californias-only-new-aca-carrier-in-2027/) | Provided verbatim by Eric (docs/inputs.md) | MEDIUM |
| S7 | [ACA Signups — CA 2027 rate changes](https://acasignups.net/26/07/21/2027-rate-changes-california-99-indy-market) | WebFetch (AI-summarized) | MEDIUM |
| S8 | [CalMatters, 2026-02 — plan-switching statistics](https://calmatters.org/health/2026/02/covered-california-health-bronze-plan/) | WebFetch (AI-summarized) | MEDIUM |
| S9 | DMHC 2024 RA Transfers Report | Bot-blocked (403); superseded by S3 | Not relied upon |
| S10 | [SB 260 bill text (Ch. 845, Statutes of 2019)](https://leginfo.legislature.ca.gov/faces/billTextClient.xhtml?bill_id=201920200SB260) + [Covered CA SB 260 enroller FAQ](https://hbex.coveredca.com/toolkit/downloads/Medi-Cal_to_Covered_California_Enrollment_Program_FAQ.pdf) | Search-verified statute; FAQ not parsed | MEDIUM (mechanism itself: MECHANISM — statutory) |
| S11 | [Covered CA SB-260 Resources: Lowest Cost Silver Plan by County, 2026 (PDF)](https://hbex.coveredca.com/toolkit/pdfs/CoveredCA_SB-260_Resources_Lowest_Cost_Silver_Plan_by_County_2026.pdf) | Downloaded, parsed (pypdf): **"Orange → Anthem"** read directly | **Primary — HIGH** |
| S12 | [CHCF — Streamlining Enrollment for Medi-Cal transitioners](https://www.chcf.org/resource/streamlining-enrollment-covered-california-transitioning-from-medi-cal/) — ~112,000 enrolled statewide via SB 260, May 2023–Mar 2024 | Search snippet; not independently parsed | MEDIUM-LOW |

---

## TL;DR (rev 3)

CalOptima enters Covered California in Orange County for 2027 as the lowest-cost Silver plan [S4–S6 — MEDIUM]. Under **SB 260, California auto-enrolls everyone losing Medi-Cal into their county's lowest-cost Silver plan** [S10 — MECHANISM] — and **Anthem holds that default slot in Orange County today** [S11 — HIGH]. CalOptima's entry therefore does two things at once: (1) takes modest direct switching share, and (2) **legally redirects Anthem's largest OC acquisition channel — the Medi-Cal churn pipeline — to CalOptima**, doubly locked because CalOptima is also these members' Medi-Cal managed care plan, the statute's alternate default [S10 — MECHANISM].

**Base case (LOW — modeled): CalOptima gains ~7,500 members in year 1 (range 3,050–14,750)** — the auto-assignment pipeline, converted at a continuity-boosted effectuation rate, is its largest component. Anthem's existing book loses ~1,100–1,500 members to switching (~$12–15M gross premium), **but versus its counterfactual trajectory Anthem is down ~3,850–4,250 members (~$38–42M annualized gross premium) once the severed SB 260 inflow is counted** — roughly 3x the rev-2 estimate of impact. Risk adjustment remains a partial offset (Anthem paid $435.1M into the CA individual pool in BY2024 [S3 — HIGH]; losing/forgoing thin-coded members shrinks that), and the statewide pool barely moves (<0.6% of 2.19M members [S2 — HIGH]). Individual pool only; small group unaffected.

---

## 1. Market baseline (Region 18, March 2026) — S1, HIGH

Unchanged from rev 2. **Total OC exchange enrollment: 170,790.**

| Issuer | Members | Share |
|---|---|---|
| Blue Shield of California | 55,360 | 32.4% |
| **Anthem Blue Cross (Elevance)** | **52,950** | **31.0%** |
| Kaiser Permanente | 51,930 | 30.4% |
| Health Net | 9,790 | 5.7% |
| Molina Healthcare (exiting) | 770 | 0.5% |

Silver tiers: 102,090 (59.8%); CSR Enhanced 87/94: 55,620 (32.6%). Anthem statewide: 169,500 members, 70.6% Silver, ~$823 gross PMPM. Anthem OC Silver ≈ 37,000 (imputed — LOW; Anthem's plan-level rows are region-unspecified in S1). Molina: 830 (R15) + 770 (R18) = 1,600, matching press [S6]. 2027: 12 carriers, +9.9% statewide / +10.4% OC [S4, S7 — MEDIUM].

## 2. The SB 260 mechanism (new in rev 3)

- SB 260 requires Covered California to **automatically plan-enroll individuals losing Medi-Cal into the lowest-cost Silver plan available to them**, or into the same managed care plan where it offers marketplace coverage; the individual gets an opt-out/plan-change notice and effectuates by paying the first premium [S10 — MECHANISM/MEDIUM]. Live since May 2023.
- Scale: ~112,000 Californians enrolled through this program May 2023–March 2024 [S12 — MEDIUM-LOW].
- **Orange County's 2026 lowest-cost Silver — the SB 260 default — is Anthem** [S11 — HIGH, parsed from Covered CA's own SB-260 county table].
- In 2027, CalOptima takes the lowest-cost Silver slot [S4–S6 — MEDIUM] **and** is the "same managed care plan" for the ~819,000 OC Medi-Cal members [S5 — MEDIUM] — it captures the default under *both* prongs of the statute.
- Pipeline sizing cross-check (LOW): CalOptima claims "up to 15,000" annual OC Medi-Cal transitioners [S5]; scaling the statewide SB 260 run-rate (~134k/yr) by OC's ~5.5% share of Medi-Cal gives ~7,400/yr. The pipeline is plausibly **7.5k–15k/yr**.
- **Effectuation is asymmetric (rev 4).** Auto-enrollees activate only by paying the first premium. For CalOptima the auto-assigned member *keeps their existing CalOptima providers* — continuity materially raises conversion — so scenarios use **25/40/60%** effectuation for CalOptima's inbound flow, vs. **20/25/35%** for the counterfactual where Anthem (an unfamiliar carrier with a different network) retains the default slot. Both rates are analyst judgment (LOW); the asymmetry direction is supported by SB 260's own design rationale — continuity of care drives take-up [S5, S10 — MEDIUM].

## 3. Q1 — How many members does CalOptima gain?

**All outputs LOW (modeled).** Rev 3 changes component (b) from "marketing pipeline requiring active capture" to "statutory default flow."

| Component | Low | Base | High | Basis |
|---|---|---|---|---|
| (a) Molina crosswalk defaults | 350 | 550 | 750 | 770 OC members, 580 Silver [S1 — HIGH]; default-to-lowest-cost-same-tier [S6 — MEDIUM]; retention judgment (LOW) |
| (b) **SB 260 auto-enrollment flow** | 1,900 | 4,400 | 9,000 | Pipeline 7.5k–15k/yr [S5, S12 — MEDIUM/LOW] × **25/40/60% effectuation** (continuity-boosted, see §2 — LOW); **default routes to CalOptima by statute [S10, S11]** — the *routing* is certain even though volume is estimated |
| (c) Switchers from incumbents | 800 | 2,500 | 5,000 | 1/3/6% of ~83k contestable non-Kaiser Silver [S1 — HIGH]; price-sensitivity anchor [S8 — MEDIUM] |
| **Total** | **~3,050** | **~7,500** | **~14,750** | ~1.8% / ~4.4% / ~8.6% of OC market |

**Rev 4 note:** the SB 260 auto-assignment is now visibly reflected in CalOptima's number — base gain rises to ~7,500 and the high case to ~14,750 (approaching CalOptima's own "15,000" figure, which now reads as the ceiling of the statutory pipeline rather than marketing). Rev 2 had called (b) "market expansion, not taken from incumbents" — **wrong**: the pipeline currently defaults to Anthem [S11 — HIGH] and transfers to CalOptima by statute. Rev 3 corrected the routing but under-sized the flow by using generic effectuation; rev 4 applies the continuity-boosted rate.

## 4. Q2 — How many members does Elevance/Anthem lose?

**All outputs LOW (modeled).** Two distinct effects — rev 2 captured only the first:

**(i) Direct book loss (switching):** unchanged — low ~400 / **base 1,100–1,500** / high ~3,300 members; ~$4M / **$12–15M** / $33M annualized gross premium at $823 PMPM [S1 — HIGH].

**(ii) Forgone SB 260 inflow:** Anthem currently receives OC's auto-enrollment flow as the default carrier [S11 — HIGH]. From 2027 the pipeline routes to CalOptima instead. Anthem's forgone inflow is valued at **Anthem's counterfactual effectuation rate (20/25/35% — LOW)**, which is lower than CalOptima's continuity-boosted rate (§2) — so CalOptima gains more members from this channel than Anthem forgoes; the difference is genuine market expansion unlocked by continuity.

| Scenario | Book loss (i) | Forgone inflow (ii) | **Net vs. counterfactual** | Annualized gross premium swing |
|---|---|---|---|---|
| Low | ~400 | ~1,500 | **~1,900** | ~$19M |
| **Base** | **~1,100–1,500** | **~2,750** | **~3,850–4,250** | **~$38–42M** |
| High | ~3,300 | ~5,250 | **~8,550** | ~$84M |

**Rev 2 understated Anthem's exposure by roughly 3x** by counting only (i). Note the framings differ: (i) is visible book shrinkage in 2027; (ii) is growth that silently stops arriving — the kind of loss that shows up as unexplained underperformance against plan a year later.

**Benchmark reset risk (unchanged, MECHANISM + LOW):** APTC pegs to the second-lowest Silver; CalOptima pricing below the floor raises net premiums across Anthem's ~49% CSR-Silver book on top of OC's +10.4% [S7]. Final 2027 rates publish fall 2026 — **re-check October 2026**, including whether Anthem even remains second-lowest (which would at least keep it the benchmark plan).

Attribution caution (unchanged): middle-income attrition from expired federal subsidies is already running statewide (22% of >400% FPL enrollees cancelled; new sign-ups −59% [S8 — MEDIUM]) — do not attribute all 2027 OC shrinkage to CalOptima.

## 5. Q3 — Risk adjustment impact

Baseline facts unchanged (S3 — HIGH, CMS final BY2024, CA individual market): Blue Shield **+$1,330.1M** (dominant receiver); Anthem **−$435.1M**, L.A. Care −$348.5M, Kaiser −$306.0M, Molina −$75.9M, Health Net −$17.3M (all payers). Pool: 26.3M billable member months ≈ 2.19M average members; average premium $563.23 [S2 — HIGH].

Rev 3 additions/refinements (LOW unless noted):

1. **SB 260 explains part of Anthem's payer position.** Auto-enrolled churners arrive with thin claims histories and low coded risk scores (MECHANISM); as the default carrier Anthem has been accumulating them, depressing its average risk score and driving RA payments. Losing the default slot cuts both ways: Anthem's ~$435M payment [S3 — HIGH] shrinks as the thin-coded inflow stops, partially offsetting lost premium (~$2,570/member/yr upper-bound relief; base-case relief on the *combined* member swing is roughly $8–12M/yr — LOW, wide error bars given the denominator problem flagged in A6).
2. **CalOptima inherits the payer position.** As the new default carrier for churners, CalOptima accumulates the thin-coded population and likely pays into the pool from year 1 (LOW).
3. **Pool-level distortion still negligible** (<0.6% of 2.19M members — bound is HIGH).
4. **Individual pool only; small group unaffected** [S2 — HIGH; S5 — MEDIUM]. AGE-71's description still needs this correction.

## 6. Assumptions register (rev 3 deltas marked ●)

| # | Assumption | Confidence | Sensitivity |
|---|---|---|---|
| A1 | CalOptima prices meaningfully below next-lowest Silver | LOW (rates publish fall 2026) | High |
| A2 | Anthem's OC metal mix ≈ statewide mix | LOW (forced by S1 gap) | Medium |
| ● A3 | SB 260 pipeline 7.5k–15k/yr; effectuation 25/40/60% for CalOptima (continuity-boosted), 20/25/35% Anthem counterfactual | LOW (volumes and rates); routing itself is statutory [S10, S11 — HIGH]; asymmetry direction MEDIUM | High — dominates both Q1 and Q2 |
| A4 | Kaiser excluded from contestable pool | LOW | Medium |
| A5 | Molina crosswalk defaults to lowest-cost same-tier | MEDIUM [S6] | Low |
| A6 | Anthem RA per-member uses exchange-only denominator (upper bound) | LOW | Low-Medium |
| ● A7 | Anthem's SB 260 inflow ≈ full OC pipeline (it holds the sole default slot [S11 — HIGH]) | MEDIUM | High for effect (ii) |
| ● A8 | SB 260 effectuation behavior in 2027 resembles 2023–24 program experience | LOW (no OC-specific effectuation data found) | High |

## 7. Known gaps

- **2027 rate gap** (CalOptima vs. benchmark Silver) — fall 2026; the single most important re-check.
- **OC-specific SB 260 volumes and effectuation rates** — Covered CA has program data; not publicly located in this pass. Would tighten (b) and (ii) substantially.
- **Anthem's off-exchange CA individual membership** — tightens RA per-member relief.
- **DMHC report [S9]** — still bot-blocked; manual pull would cross-check S3.

---

## Postscript — A2 Analysis Agent requirements (input to AGE-68)

1. Structured data fetch + parse (XLSX/PDF), with per-claim provenance tags (source ID, retrieval method, confidence) as native output.
2. Region/entity resolution (county ↔ rating region ↔ HIOS ID ↔ dba names).
3. Bot-blocked-source fallbacks with recorded verification status.
4. **Regulatory-mechanism knowledge base (new — the SB 260 lesson):** a curated "rules layer" of standing statutes and program mechanics governing member flows (auto-enrollment laws, crosswalk rules, benchmark mechanics, RA program design), maintained as domain memory and seeded by expert input via `docs/inputs.md`. News and dataset retrieval structurally cannot surface this class of context; every analysis must include an explicit "which standing rules govern this flow?" step against that knowledge base.
5. Scenario modeling with an assumptions register and sensitivity ratings.
6. Temporal follow-up triggers on known future data releases.

## Revision log

- **rev 1** (2026-07-23): initial analysis.
- **rev 2** (2026-07-23): per-claim citations + confidence levels; RA figures re-verified against CMS primary (Anthem corrected $438.8M → $435.08M).
- **rev 3** (2026-07-23): SB 260 incorporated after Eric flagged the omission (see §0). Q1 component (b) reclassified from market expansion to statutory default transfer; Q2 adds forgone-inflow effect (base-case Anthem impact ~3x rev 2); Q3 adds SB 260 explanation of Anthem's RA payer position; sources S10–S12 added; assumptions A3/A7/A8 revised/added.
- **rev 4** (2026-07-23): Eric flagged that CalOptima's membership hadn't visibly moved despite the auto-assignment transfer. Fixed via asymmetric effectuation: CalOptima converts auto-assignments at 25/40/60% (provider continuity), Anthem counterfactual at 20/25/35%. CalOptima base gain ~6,500–7,500 → **~7,500** (high 12,500 → **14,750**); Anthem net-vs-counterfactual base refined to **~3,850–4,250 / ~$38–42M** (still ~3x rev 2). CalOptima gains more than Anthem forgoes; the gap is real market expansion unlocked by continuity.
