# Regulatory Rules Layer

This document is the agent's curated knowledge base of standing regulatory mechanisms governing health insurance member flows. It is read in full by `lookup_regulatory_rules()` before any data pull.

Matt seeds and maintains this document. No code change required to add a new state or program.

Each entry contains: (1) the mechanism in plain language, (2) its effect on member flows, (3) where evidence might be found.

---

## California — ACA Individual Market (Covered CA)

### SB 260 — Medi-Cal to Covered CA Auto-Enrollment

**Mechanism:** California SB 260 (2019) requires that individuals losing Medi-Cal eligibility who do not actively choose a health plan be automatically enrolled in the lowest-cost Silver plan available in their county. The carrier offering the lowest-cost Silver in a given county holds the "default slot" and receives these members automatically — no marketing, no active member choice required.

There are two pathways under SB 260:
1. **Primary default:** lowest-cost Silver by county (price-determined)
2. **Alternate default:** the member's existing Medi-Cal managed care plan, if that plan offers a Covered CA product in the county — this pathway takes precedence over the price-based default

**Effect on member flows:** The carrier holding the default slot receives a steady inflow of thin-coded, newly-insured members at no marketing cost. Losing the default slot severs this acquisition channel entirely. The loss is not visible as attrition — it surfaces as unexplained underperformance against growth plan.

**Anthem relevance:** Anthem currently holds the OC default slot (PY2026). If a new entrant becomes lowest-cost Silver in OC, the statutory default transfers to them. If a Medi-Cal plan (e.g., CalOptima) enters Covered CA and triggers the alternate-default pathway, the transfer is doubly locked.

**Evidence:**
- Covered CA publishes a county-level default-holder table annually. Search coveredca.gov for "SB-260 Lowest Cost Silver Plan by County" — typically a PDF in the toolkit section.
- Medi-Cal transition pipeline volume: DHCS and KFF publish county-level redetermination estimates.
- Enrollment baseline by carrier: Covered CA Active Member Profile XLSX (monthly).

---

### Benchmark Silver Mechanics — APTC Pegging

**Mechanism:** Advanced Premium Tax Credits (APTC) are calculated as the difference between the second-lowest-cost Silver plan premium (the "benchmark") and the household's income-based contribution. When a new entrant undercuts the benchmark Silver, the benchmark resets downward. All subsidized members on more expensive plans face higher net premiums — not just those on the new entrant's plan.

**Effect on member flows:** A benchmark reset creates market-wide switching pressure across all incumbent carriers, not just against the new entrant. Silver-tier members on CSR-enhanced plans (87, 94) are most affected because their plan selection is constrained to Silver. If Anthem is the benchmark or above-benchmark carrier, its subsidized Silver members face increased net cost.

**Anthem relevance:** Anthem's OC book is approximately 71% Silver, ~49% CSR-enhanced. A benchmark reset hits a majority of the book simultaneously.

**Evidence:**
- Covered CA 2027 rate announcements (typically July of prior year). Search coveredca.gov for rate filings by region.
- CMS APTC data by county/region.

---

### Medi-Cal Continuous Enrollment Unwinding

**Mechanism:** During COVID, federal law prohibited Medi-Cal disenrollments. The unwinding of this continuous enrollment requirement (beginning 2023, ongoing through 2025-2026) has generated a large wave of Medi-Cal eligibility redeterminations. Members losing Medi-Cal become eligible for Covered CA subsidies; SB 260 auto-enrollment applies to those who do not actively choose a plan.

**Effect on member flows:** Ongoing source of new-to-marketplace members. CalOptima's Medi-Cal members who lose eligibility and don't actively choose a plan would default to CalOptima's Covered CA product (if available) via the alternate-default pathway.

**Evidence:**
- DHCS publishes monthly redetermination data. KFF tracks statewide and county-level unwinding figures.
- Search "Medi-Cal unwinding Orange County redeterminations 2025 2026."

---

### Silver Loading

**Mechanism:** Because APTC only applies to Silver plans, carriers sometimes price Silver higher than actuarially warranted ("load" the Silver tier) to maximize the value of subsidies for enrollees. Members on Bronze or Gold plans effectively get cheaper coverage because APTC is pegged to Silver.

**Effect on member flows:** Silver loading can make Gold plans cheaper than Silver for many members — creating unexpected switching patterns. A new entrant choosing not to Silver-load can undercut the benchmark without being cheaper on a true actuarial basis.

**Evidence:** Rate filings — compare Silver and Gold premiums. If Gold < Silver for a carrier, Silver loading is occurring.

---

## California — Medicaid (Medi-Cal)

### Medi-Cal Managed Care — County Organized Health Systems (COHS)

**Mechanism:** Several California counties operate County Organized Health Systems (COHS) — single-plan mandatory Medi-Cal systems where one county-affiliated plan serves all Medi-Cal beneficiaries. Orange County uses this model (CalOptima is the COHS). Members have no plan choice.

**Effect on member flows:** CalOptima has a captive Medi-Cal population in OC. Every Medi-Cal member who transitions to Covered CA in OC has an existing relationship with CalOptima. This is the foundation of CalOptima's SB 260 alternate-default advantage.

**Evidence:** DHCS managed care enrollment reports. CalOptima's own published membership figures.

---

### Medi-Cal Capitation Rates

**Mechanism:** DHCS sets per-member per-month capitation rates for Medi-Cal managed care plans by county and aid category. Rates are negotiated and set annually.

**Evidence:** DHCS publishes capitation rate schedules. Not always publicly available at the county level — Matt may need to provide from Elevance contract data.

---

## California — ACA Individual Market: Risk Adjustment (Federal)

### HHS Risk Adjustment Program (ACA, all states)

**Mechanism:** The federal risk adjustment program transfers funds from plans with lower-risk enrollees to plans with higher-risk enrollees within the same state market (individual, small group separately). The transfer is calculated using the HHS-HCC risk score model. A plan that enrolls healthier-than-average members pays into the pool; a plan with sicker-than-average members receives transfers.

**Effect on member flows:** New entrants (like CalOptima year 1) typically enroll younger, healthier members who are new to marketplace coverage. Their risk scores run low, making them likely payers into the RA pool. Incumbent carriers losing healthy members to new entrants see their average risk score rise, receiving more from the pool — a partial financial offset to premium revenue lost.

**Anthem relevance:** Anthem is a large payer into the CA individual market RA pool (BY2024: -$435M). Losing price-sensitive, thin-coded SB 260 members shrinks Anthem's RA payment — partial offset.

**Evidence:**
- CMS publishes annual Risk Adjustment State Summary reports. Search cms.gov for "risk adjustment state summary BY[year]."
- DMHC publishes CA-specific RA data. Search dmhc.ca.gov.

---

## Medicare Advantage (all states)

### CMS Plan Approval Process

**Mechanism:** MA carriers must submit plan bids to CMS by the first Monday in June each year. CMS reviews and approves service areas (counties) and benefits. Marketing to members cannot begin until CMS approval is received (typically September/October). Plans cannot publicly name the specific counties they are filing for until after CMS approval.

**Effect on member flows:** "Two unnamed states" or "pending regulatory review" in an MA announcement means a CMS filing is in progress, not that the states are secret. The specific counties become public upon CMS approval. Filing date + typical approval timeline (~3-4 months) gives an approximate reveal date.

**Evidence:** CMS publishes approved plan service areas annually. Search cms.gov for "Medicare Advantage plan service area" or "HPMS." CMS bid submission deadline is public.

---

### MA Star Ratings

**Mechanism:** CMS rates MA plans 1-5 stars annually. Plans with 4+ stars receive quality bonus payments (~5% premium uplift). Plans below 3 stars face potential termination. Star ratings affect member retention (low-star plans lose members at disenrollment), benchmark rates, and carrier revenue.

**Evidence:** CMS publishes star ratings annually (October). Search cms.gov for "Medicare Advantage star ratings [year]."

---

## Multi-State

### Network Adequacy Requirements

**Mechanism:** State DOIs and CMS require carriers to demonstrate network adequacy (sufficient in-network providers per covered member). Entering a new geographic market requires establishing provider contracts. Provider network gaps are a common reason for delayed or denied market entry.

**Evidence:** State DOI filings. CMS network adequacy reports for MA. Not always public.
