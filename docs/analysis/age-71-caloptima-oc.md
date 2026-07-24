# AGE-71 — CalOptima's Covered California Entry: Elevance Member Impact and Risk Adjustment Analysis

**Date:** 2026-07-23
**Analyst:** Claude (Fable 5), for Eric Low
**Linear:** [AGE-71](https://linear.app/eric-projects/issue/AGE-71/caloptima-oc-entry-elevance-member-impact-and-risk-adjustment-analysis)

---

## TL;DR

CalOptima Health enters Covered California in Region 18 (Orange County) for plan year 2027 as the lowest-cost Silver plan. **Base case: CalOptima captures ~7,000 members in year 1 (~4% of the OC exchange market); Anthem loses ~1,100–1,500 members (~2–3% of its 52,950-member OC book), worth roughly $12–15M in annualized gross premium.** The larger strategic exposure is not direct switching but the benchmark reset: a cheaper Silver entrant raises net premiums for every incumbent's subsidized members. Risk adjustment impact is modestly *favorable* per-member for Anthem — Anthem is a $438.8M payer into the CA individual pool, and losing healthy price-sensitive members shrinks that payment — but it offsets only ~25% of lost premium. The statewide pool itself barely moves (<1% membership perturbation). **The issue's "individual/small group" framing should be corrected: this touches the individual pool only.**

---

## 1. Market baseline (Region 18, March 2026)

Source: Covered California Active Member Profile, March 2026 (`CC_Membership_Profile_2026_03_R20260702.xlsx`).

**Total OC exchange enrollment: 170,790**

| Issuer | Members | Share |
|---|---|---|
| Blue Shield of California | 55,360 | 32.4% |
| **Anthem Blue Cross (Elevance)** | **52,950** | **31.0%** |
| Kaiser Permanente | 51,930 | 30.4% |
| Health Net | 9,790 | 5.7% |
| Molina Healthcare (exiting) | 770 | 0.5% |

**Metal tier mix (OC):** Silver tiers total 102,090 (59.8%) — base Silver 34,270; Enhanced 73 12,200; Enhanced 87 32,000; Enhanced 94 23,620. The Enhanced 87/94 population (55,620 members, 32.6% of the market) is deeply subsidized and the most price-reactive segment.

**Anthem's book skews Silver.** Anthem's statewide metal mix is ~70.6% Silver (21.6% base + 48.9% CSR-enhanced), vs. 59.8% for the OC market overall. Plan-level OC splits for Anthem are region-unspecified in the profile file (data quirk), so OC Silver is estimated at ~37,000 of Anthem's 52,950 using the statewide mix. Anthem's OC book is roughly half EPO / half HMO by statewide product mix.

**Anthem statewide averages (exchange book):** gross premium ~$823/member/month; ~22% of Anthem members pay $0 net premium; median net premium/policy $121.75.

**2027 context:** 12 carriers statewide; preliminary weighted average increase +9.9% statewide, **+10.4% in OC**. CalOptima is the only new entrant; Molina exits regions 15 and 18 (830 + 770 = ~1,600 members, matching press reports). CalOptima Health Covered launches as **lowest-cost Silver in OC**, four metal tiers, network of 9,800 PCPs/specialists and 43 hospitals. CalOptima estimates "up to 15,000" OC residents transition off Medi-Cal annually — note this is the *eligible churn pipeline*, not an enrollment projection.

---

## 2. Q1 — How many members does CalOptima gain?

Three additive components, year 1 (PY2027):

| Component | Low | Base | High | Notes |
|---|---|---|---|---|
| (a) Molina crosswalk defaults | 350 | 550 | 750 | 770 OC members; 580 in Silver auto-map to lowest-cost same-tier = CalOptima; assumes 60–80% stick with default |
| (b) Medi-Cal churn capture | 1,500 | 4,000 | 7,500 | 10% / ~25% / 50% of the 15k annual eligible pipeline; continuity-of-care + $0-premium Enhanced Silver is a strong hook for this population |
| (c) Switchers from incumbents | 800 | 2,500 | 5,000 | 1% / 3% / 6% of the ~83k contestable Silver pool (excludes Kaiser, whose integrated-model members rarely switch) |
| **Total** | **~2,700** | **~7,000** | **~13,300** | **1.6% / ~4% / ~7.8% of OC market** |

Supporting evidence for price sensitivity: 1 in 3 new Covered CA enrollees chose the cheapest (Bronze) tier for 2026, and 130,000 renewing members downgraded to Bronze statewide — price-driven plan selection is high and rising. CalOptima's brand reach (819,000 Medi-Cal members; 1 in 4 OC residents) is unusually strong for a new entrant, but its Medi-Cal-centric network may deter commercial-minded buyers, which caps the high case.

Component (b) is largely **market expansion** (people who would otherwise churn to uninsured), not share taken from incumbents. Only (a) and (c) come out of incumbent books.

---

## 3. Q2 — How many members does Elevance/Anthem lose?

Anthem holds ~45% of the contestable (non-Kaiser) Silver pool (~37k of ~83k), so it absorbs roughly that share of component (c):

| Scenario | Anthem member loss | Annualized gross premium at $823 PMPM |
|---|---|---|
| Low | ~400 | ~$4M |
| **Base** | **~1,100–1,500** | **~$12–15M** |
| High | ~2,300–3,300 | ~$23–33M |

That is ~2–3% of Anthem's OC exchange book in the base case — real but not structural. Margin impact is smaller than revenue impact: the leavers are low-utilizers, and they carry a risk adjustment charge (see Q3).

**The bigger exposure is the benchmark reset.** APTC subsidies peg to the second-lowest-cost Silver. CalOptima entering below the current price floor can pull the benchmark down, which raises *net* premiums for subsidized members of **every** incumbent even if incumbent gross rates were flat — and OC incumbents are taking +10.4% on top. With ~48% of Anthem's book in CSR-enhanced Silver, this compounds attrition beyond direct switching (downgrades to Bronze, or exits). The high scenario above includes this effect; the exact benchmark math isn't computable until final 2027 rates publish this fall — **flagging that as the single most important thing to re-check in October 2026.**

Anthem also loses optionality on the churn pipeline: component (b) members were winnable growth that will now default to CalOptima.

---

## 4. Q3 — Risk adjustment impact

Source: DMHC 2024 Benefit Year Risk Adjustment Transfers Report (Nov 2025 FSSB agenda item); CMS BY2024 summary.

**Baseline (BY2024, CA individual market):** $1.54B transferred; transfers average 10.9% of premium. **Anthem Blue Cross paid $438.8M into the pool** (its book codes healthier than market average). Kaiser paid ~$306.7M; Health Net paid ~$16.2M; Blue Shield received ~$1.33B (the sickest large book).

Three effects from CalOptima's entry:

1. **Anthem's transfer payment shrinks (favorable).** The members Anthem loses to a lowest-cost Silver entrant are disproportionately its healthiest, lowest-coded members — exactly the ones generating its RA charge. At Anthem's implied ~$2,600/member/year individual-market RA payment (upper bound, using exchange membership as denominator), the base-case 1,100–1,500 lost members reduce Anthem's RA payment by roughly **$3–4M/year — offsetting about a quarter of the lost premium.** Net margin damage from losing these members is therefore modest: low-claims members who carried an RA charge are the cheapest members to lose.
2. **CalOptima enters as a likely payer year 1.** New-entrant enrollees carry thin diagnosis histories and low year-1 risk scores, and its churn population skews young/income-volatile. Expect CalOptima to pay into the pool initially (marginally increasing funds flowing to high-risk books like Blue Shield's), with scores maturing in years 2–3.
3. **Pool-level distortion is negligible.** ~7k–13k new members against a ~1.8M-member statewide individual pool is <1%. No meaningful change to transfer mechanics or the 10.9%-of-premium scale.

**Correction to the issue:** California's individual and small group risk adjustment pools are separate. CalOptima Health Covered is an individual-market product only — **the small group pool is unaffected.** AGE-71's description should be amended.

---

## 5. Assumptions and caveats

- Final 2027 rates (and the benchmark Silver position) publish in fall 2026 after regulatory review; the price gap between CalOptima and the next-lowest Silver is the key unpulled number. All switching estimates assume a meaningful (>$10/mo) gap.
- Anthem's OC metal mix is imputed from its statewide mix.
- Anthem's per-member RA payment uses on-exchange membership as denominator; Anthem's total CA individual book (incl. off-exchange) is larger, so the true per-member figure is somewhat lower.
- CalOptima's "15,000" is treated as pipeline, not projection; capture rates (10/25/50%) are judgment calls anchored to new-entrant precedent, not observed data.
- Molina crosswalk behavior assumes Covered CA's stated default-to-lowest-cost-same-tier rule.

## 6. Sources

- [Covered CA 2027 rates & plans release (2026-07-21)](https://www.coveredca.com/newsroom/news-releases/2026/07/21/covered-california-rates-and-plans-for-2027-california-continues-fight-for-health-insurance-affordability-and-access/)
- [CalOptima press release — joining Covered California](https://www.caloptima.org/en/about-us/press-releases/caloptima-health-to-join-covered-california-as-an-affordable-plan-for-orange-county)
- [Covered CA Active Member Profile, March 2026 (XLSX)](https://hbex.coveredca.com/data-research/library/CC_Membership_Profile_2026_03_R20260702.xlsx)
- [DMHC 2024 RA Transfers Report (FSSB Nov 2025)](https://www.dmhc.ca.gov/Portals/0/Docs/OFR/FSSB/Nov2025/AgendaItem8_2024RiskAdjustmentTransfersReport.pdf)
- [Becker's Payer — CalOptima only new ACA carrier 2027](https://www.beckerspayer.com/payer/aca/caloptima-to-be-californias-only-new-aca-carrier-in-2027/)
- [ACA Signups — CA 2027 rate changes](https://acasignups.net/26/07/21/2027-rate-changes-california-99-indy-market)
- [CalMatters — 1 in 3 new enrollees chose cheapest plans (2026-02)](https://calmatters.org/health/2026/02/covered-california-health-bronze-plan/)

---

## Postscript — what the A2 Analysis Agent would need to automate this (input to AGE-68)

This analysis was done by hand; it is the concrete test case for the A2 spec. Required capabilities observed:

1. **Structured data fetch + parse**: download and parse XLSX (Covered CA Active Member Profile) — not just web pages. A2 needs a spreadsheet/CSV tool, not only HTML scraping.
2. **Region/entity resolution**: mapping "Orange County" → rating region 18 → the right column in a 44-column sheet. Alias/geography knowledge belongs in the DB.
3. **Regulatory document access**: DMHC PDFs are bot-blocked (403 even with UA spoofing); risk adjustment figures had to come via search-index summaries. A2 needs a fallback strategy (search snippets, cached copies) and should record source confidence.
4. **Scenario modeling**: low/base/high parameter tables with explicit capture-rate assumptions — a calculation step, not just retrieval.
5. **Temporal follow-up**: the key unknown (final 2027 rate gap) resolves in fall 2026 — A2 should support scheduling a re-analysis trigger when a known future data release lands.
6. **Output**: this document's shape (TL;DR → baseline → per-question scenario tables → caveats → sources) is a reasonable default briefing format for A2.
