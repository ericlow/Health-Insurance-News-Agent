# News Source Evaluation Catalog

_Last updated: 2026-07-11 | AGE-55_

This document catalogs candidate news sources for the Health Insurance News Agent beyond the current Becker's Payer implementation. The domain expert reviews this doc and decides which sources to add scrapers for next.

**Target states:** CA, NV, CO, MO, WI, NY, NJ

---

> **Scope note for domain expert review:** The triage prompt in `agent/triage.py` covers **7 target states** (including NY and NJ) and **16 signal categories** — broader than the original PRD's focus on carrier/provider relationship changes. The additional categories include: ACA changes (categories 1, 14), universal healthcare/MFA proposals (2, 10, 15), federal-to-state funding shifts (3, 12), GLP-1 drug costs (13), mental health mandates (11), and labor unions (16). Sources in this catalog are tagged accordingly. **Before adding parsers for Sections H–J** (national policy, GLP-1/PBM, labor), please confirm whether those signal categories are in scope — they are market context signals rather than direct relationship change signals, and may generate noise against the current triage logic.

---

## How to Read This Doc

Each source entry includes:

| Field | What it means |
|-------|---------------|
| **Category** | trade press / carrier newsroom / provider newsroom / government-regulatory / state-regional |
| **Access barrier** | free · free-with-registration · subscription-only · paywalled |
| **Technical complexity** | RSS (easiest) → plain HTTP → JS-rendered → Cloudflare-blocked (hardest) |
| **Signal types** | kinds of events this source covers — see legend below |
| **State relevance** | which target states this source covers |
| **Leading indicator** | Y = publishes pre-announcement signals (layoffs, RFPs, soft signals); N = confirmed news only |
| **Expected volume** | rough estimate of relevant articles per week |
| **Priority tier** | 1 = add next · 2 = add later · 3 = aware but blocked or low ROI |

**Signal type legend** — mapped to the triage prompt's 16 categories:

Relationship changes (state-level):
- `network` — partnerships, new network agreements, or contract terminations / network exits (categories 5, 7)
- `M&A` — acquisitions, mergers, divestitures, spin-offs (categories 4, 6)
- `TPA` — TPA or administrator switches by large employers (category 8)
- `layoffs` — workforce reductions (leading indicator of contract loss; personnel signal category D exception applies when role change signals a deal)
- `provider-plan` — provider building its own insurance product (signals future network exits)

Policy and regulatory:
- `ACA` — Affordable Care Act changes, marketplace participation (categories 1, 14)
- `MFA` — universal healthcare, Medicare for All, single-payer proposals (categories 2, 10, 15)
- `federal-shift` — federal responsibilities or funding moving to state level (categories 3, 12)
- `mental-health` — mandated mental health or behavioral health benefits (category 11)
- `regulatory` — enforcement actions, fines, plan approvals

Cost and market drivers:
- `GLP-1` — GLP-1 drug coverage and cost impact (category 13)
- `labor` — labor unions, strikes, contract negotiations affecting healthcare coverage (category 16)
- `procurement` — RFPs, purchaser contract signals (CalPERS, unions, large employers)

---

## A. Trade Press

### Fierce Healthcare — Payer Section + Layoff Tracker

| Field | Value |
|-------|-------|
| **URL** | https://www.fiercehealthcare.com/payer |
| **Layoff Tracker** | https://www.fiercehealthcare.com/finance/fierce-healthcare-layoff-tracker |
| **Category** | trade press |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP (no Cloudflare); RSS available at `/rss/payer` |
| **Signal types** | `network` `M&A` `layoffs` `regulatory` `GLP-1` `labor` |
| **State relevance** | all — national coverage, flags CA/NY/NJ-specific events |
| **Leading indicator** | Y — Layoff Tracker explicitly covers account team reductions; this is the direct feed for the "United laid off the CalPERS team" pattern |
| **Expected volume** | medium (3–5 relevant articles/week) |
| **Priority tier** | 1 |
| **Notes** | The Layoff Tracker is a dedicated, continuously updated page — consider a separate scraper for it. Payer section RSS should be accessible without Playwright. |

---

### Healthcare Dive — Payers Topic

| Field | Value |
|-------|-------|
| **URL** | https://www.healthcaredive.com/topic/payers/ |
| **Category** | trade press |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP; RSS available at `/feeds/` |
| **Signal types** | `network` `M&A` `regulatory` `ACA` `GLP-1` |
| **State relevance** | all — national with state call-outs |
| **Leading indicator** | N — confirmed news, well-sourced but not early signals |
| **Expected volume** | medium (2–4 relevant articles/week) |
| **Priority tier** | 1 |
| **Notes** | Clean site, reliable RSS, good M&A and contract coverage. No Cloudflare observed. Straightforward to add as a second RSS source. |

---

### KFF Health News

| Field | Value |
|-------|-------|
| **URL** | https://kffhealthnews.org |
| **RSS** | https://kffhealthnews.org/feed/ |
| **Category** | trade press |
| **Access barrier** | free |
| **Technical complexity** | RSS available; plain HTTP |
| **Signal types** | `network` `regulatory` `procurement` `ACA` `MFA` `federal-shift` |
| **State relevance** | CA (dedicated California Bureau, absorbed California Healthline in Oct 2025), national |
| **Leading indicator** | Y — investigative journalism; publishes analysis of soft RFP signals and purchaser intent |
| **Expected volume** | low–medium (1–3 relevant articles/week) |
| **Priority tier** | 1 |
| **Notes** | California Healthline's original reporting moved here as of October 2025. KFF Health News is independently published and has no paywall. Excellent for CA-specific purchaser/regulatory signals. |

---

### Modern Healthcare — Insurance Section

| Field | Value |
|-------|-------|
| **URL** | https://www.modernhealthcare.com/insurance/ |
| **Category** | trade press |
| **Access barrier** | paywalled (limited free articles per month; summaries visible) |
| **Technical complexity** | plain HTTP for headlines; article body requires account |
| **Signal types** | `network` `M&A` `regulatory` `provider-plan` `ACA` `GLP-1` `labor` |
| **State relevance** | all — national trade press |
| **Leading indicator** | N — confirmed news; high credibility, good sourcing |
| **Expected volume** | medium (3–5 relevant articles/week) |
| **Priority tier** | 2 |
| **Notes** | Major trade publication. Paywall limits body text access. Headline + summary scraping may still be useful as a signal that a story exists, even without full text. Investigate whether RSS exposes summaries. |

---

### MedCity News

| Field | Value |
|-------|-------|
| **URL** | https://medcitynews.com |
| **RSS** | https://medcitynews.com/feed/ |
| **Category** | trade press |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP; RSS available |
| **Signal types** | `M&A` `provider-plan` `network` |
| **State relevance** | all — national, innovation-focused |
| **Leading indicator** | N — confirmed announcements; earlier signal on partnerships and provider-sponsored plans |
| **Expected volume** | low (1–2 relevant articles/week) |
| **Priority tier** | 2 |
| **Notes** | Skews toward health tech and innovation deals. Useful for provider-sponsored plan announcements and partnership deals that precede network changes. |

---

### STAT News

| Field | Value |
|-------|-------|
| **URL** | https://www.statnews.com |
| **RSS** | https://www.statnews.com/feed/ |
| **Category** | trade press |
| **Access barrier** | partially paywalled (some investigative articles free) |
| **Technical complexity** | plain HTTP for free articles; paywall for premium |
| **Signal types** | `M&A` `regulatory` `network` `ACA` `MFA` `GLP-1` `federal-shift` |
| **State relevance** | all — national investigative |
| **Leading indicator** | Y — investigative pieces sometimes break stories before official announcements |
| **Expected volume** | low (1–2 relevant articles/week) |
| **Priority tier** | 2 |
| **Notes** | Strong investigative journalism. Paywall is partial — STAT+ content is gated, general news is free. RSS accessible. Particularly strong on GLP-1 cost and formulary stories. |

---

### Health Affairs

| Field | Value |
|-------|-------|
| **URL** | https://www.healthaffairs.org |
| **Category** | trade press / academic journal |
| **Access barrier** | paywalled (institutional subscription or per-article) |
| **Technical complexity** | plain HTTP; RSS available but abstracts only |
| **Signal types** | `regulatory` `network` |
| **State relevance** | all — policy research |
| **Leading indicator** | N — academic analysis published weeks/months after events |
| **Expected volume** | very low (<1 relevant article/week) |
| **Priority tier** | 3 |
| **Notes** | Academic journal, not breaking news. By the time a Health Affairs paper covers a network change, the event is months old. Low ROI for this use case. Awareness only. |

---

## B. Industry Intelligence (Subscription-Only — Awareness Only)

### AIS Health / Health Plan Weekly

| Field | Value |
|-------|-------|
| **URL** | https://aishealthdata.com |
| **Category** | industry intelligence |
| **Access barrier** | subscription-only (no free tier) |
| **Technical complexity** | N/A — blocked without subscription |
| **Signal types** | `network` `M&A` `regulatory` — enrollment and financial data |
| **State relevance** | all — national enrollment and plan data |
| **Leading indicator** | Y — quarterly financial data per plan; membership shifts surface early |
| **Expected volume** | medium |
| **Priority tier** | 3 — blocked |
| **Notes** | The definitive source for health plan enrollment and contact data. High signal if we had access. Subscription cost is significant. Flag for future consideration if budget allows. Free newsletter digest is available — worth monitoring manually. |

---

### AHIP News

| Field | Value |
|-------|-------|
| **URL** | https://www.ahip.org/news |
| **Category** | industry intelligence / trade association |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` — payer trade association announcements |
| **State relevance** | all — national policy |
| **Leading indicator** | N — trade association press releases; industry positions, not breaking events |
| **Expected volume** | low (1–2 relevant articles/week) |
| **Priority tier** | 3 |
| **Notes** | America's Health Insurance Plans — trade association for payers. Publishes policy positions and advocacy materials. Low discovery value; confirmed industry-level announcements only. |

---

### Mark Farrah Associates — Industry News

| Field | Value |
|-------|-------|
| **URL** | https://www.markfarrah.com/industry-news-list/ |
| **Category** | industry intelligence |
| **Access barrier** | free (commentary) |
| **Technical complexity** | plain HTTP |
| **Signal types** | `M&A` `network` — market share analysis |
| **State relevance** | all — national enrollment data |
| **Leading indicator** | N — lagging analysis of enrollment shifts |
| **Expected volume** | very low (<1/week) |
| **Priority tier** | 3 |
| **Notes** | Market share data and enrollment trend commentary. Useful for context, not discovery. Slow publication cadence. |

---

## C. California Government / Regulatory (High Signal)

### CalPERS Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.calpers.ca.gov/newsroom |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `procurement` `network` `TPA` `labor` — carrier selection, RFP announcements, premium decisions |
| **State relevance** | CA |
| **Leading indicator** | Y — CalPERS publicly signals carrier intent months before changes take effect (soft RFPs, open bidding announcements) |
| **Expected volume** | low (1–3 relevant items/month) |
| **Priority tier** | 1 |
| **Notes** | CalPERS is the exact source of the United/Sutter signal that motivated this project. Newsroom publishes health plan premium decisions, carrier additions/removals, and open enrollment updates. Low volume but extremely high signal per item. No RSS — requires page scraping. |

---

### California DMHC Press Releases

| Field | Value |
|-------|-------|
| **URL** | https://www.dmhc.ca.gov/Resources/Newsroom/PressReleases.aspx |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` `mental-health` — enforcement actions, plan approvals, network adequacy orders, mental health parity enforcement |
| **State relevance** | CA |
| **Leading indicator** | Y — regulatory fines and enforcement actions often precede or accompany public network disputes (e.g., DMHC fined Cigna 500k and Anthem 3.5M within the past year) |
| **Expected volume** | low (2–4 items/month) |
| **Priority tier** | 1 |
| **Notes** | Protects 29.8M Californians. Enforcement actions against carriers are a signal of relationship strain. No RSS — plain HTML page listing press releases by date. Straightforward to scrape. |

---

### Covered California Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.coveredca.com/newsroom/news-releases/ |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `regulatory` — marketplace carrier entries/exits, enrollment shifts |
| **State relevance** | CA |
| **Leading indicator** | Y — carrier decisions to enter/exit the ACA marketplace are announced here before open enrollment |
| **Expected volume** | low (1–3 items/month) |
| **Priority tier** | 2 |
| **Notes** | ACA marketplace for CA. Carrier participation decisions (joining or leaving) are significant network events. Press releases are plain HTML, no RSS needed. |

---

### California Association of Health Plans (CAHP)

| Field | Value |
|-------|-------|
| **URL** | https://www.calhealthplans.org |
| **Category** | government-regulatory / trade association |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` — state legislation, regulatory commentary |
| **State relevance** | CA |
| **Leading indicator** | N — advocacy positions and regulatory tracking; not breaking news |
| **Expected volume** | very low (<1/week) |
| **Priority tier** | 3 |
| **Notes** | CA trade association for health plans. Useful for tracking state regulatory environment but rarely surfaces specific carrier/provider relationship news. |

---

## D. Carrier Newsrooms

> **Editorial note:** Carrier newsrooms are PR-controlled. They announce deals, partnerships, and expansions — but will not break negative news about themselves (contract losses, terminations, disputes). Use these as **confirmation signals** and **provider-plan expansion indicators**, not as primary discovery sources.

### Kaiser Permanente Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://newsroom.kaiserpermanente.org |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP; RSS likely available |
| **Signal types** | `network` `provider-plan` `M&A` |
| **State relevance** | CA, CO |
| **Leading indicator** | Y — Kaiser announces network expansions, new service areas, and partnership agreements that signal reconfiguration |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | Dominant integrated HMO in CA and CO. Kaiser expanding into new geographies or product lines is a significant market signal. |

---

### Blue Shield of California Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.blueshieldca.com/bsca/bsc/news-room/ |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `M&A` `provider-plan` |
| **State relevance** | CA |
| **Leading indicator** | N — confirmed announcements only |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | Major CA carrier. Announces new network agreements, product launches, and partnership deals. Relevant example: Blue Shield assumed CalPERS PPO administration in 2025. |

---

### Health Net Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.healthnet.com |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `regulatory` |
| **State relevance** | CA |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | very low (<1/month) |
| **Priority tier** | 2 |
| **Notes** | CA-based carrier, now a Centene subsidiary. Medi-Cal (Medicaid) and commercial coverage. Centene's CA footprint makes network changes here significant for low-income and ACA enrollees. |

---

### Elevance Health / Anthem Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.elevancehealth.com/newsroom |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `M&A` `provider-plan` |
| **State relevance** | CA, CO, MO, WI |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | Anthem operates in CA (Anthem Blue Cross), CO, MO, and WI under the Elevance Health umbrella. Network deal announcements here cross multiple target states. |

---

### UnitedHealth Group Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.unitedhealthgroup.com/newsroom.html |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `M&A` |
| **State relevance** | all target states |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | Directly relevant given CalPERS/United history. UHG newsroom is where United would announce major network or TPA changes. Monitor for CA announcements in particular. |

---

### Cigna Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://newsroom.cigna.com |
| **Category** | carrier newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP; RSS likely available |
| **Signal types** | `network` `M&A` `provider-plan` |
| **State relevance** | all target states |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | Already identified in original domain expert inputs (newsroom.cigna.com/uc-health example). Confirmed announcements of network partnerships. |

---

## E. Provider Newsrooms (Leading Indicator: Providers Building Own Plans)

> Providers announcing their own insurance products or network expansions are a leading indicator of impending network exits from existing carrier agreements. Monitor for "provider-sponsored plan" and "new network agreement" announcements.

### Sutter Health Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.sutterhealth.org/about/news |
| **Category** | provider newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `provider-plan` `network` |
| **State relevance** | CA |
| **Leading indicator** | Y — Sutter building or expanding its own plan signals network reconfiguration with existing carrier partners |
| **Expected volume** | very low (<1/month) |
| **Priority tier** | 2 |
| **Notes** | Directly referenced in CalPERS/United/Sutter example. Sutter is a major CA provider system. New plan announcements, Anthem partnership expansions, and network agreements are the signals to watch. |

---

### Intermountain Health Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://intermountainhealthcare.org/news/ |
| **Category** | provider newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `provider-plan` `network` `M&A` |
| **State relevance** | CO (primary), NV (thin presence) |
| **Leading indicator** | Y — new network agreements or plan announcements here affect CO market |
| **Expected volume** | very low (<1/month) |
| **Priority tier** | 2 |
| **Notes** | Utah-based integrated health system. Acquired SCL Health in 2022 to build CO and MT footprint (renamed Intermountain Health). NV presence is limited. CO is the primary target state signal here — monitor for acquisitions of CO provider groups or new plan launches. |

---

### Providence Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.providence.org/news |
| **Category** | provider newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `M&A` `provider-plan` |
| **State relevance** | CA, NV |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | very low (<1/month) |
| **Priority tier** | 3 |
| **Notes** | Large CA/NV provider system. Lower signal priority than Sutter or Intermountain for this use case. |

---

### CommonSpirit / Dignity Health Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.commonspirit.org/newsroom |
| **Category** | provider newsroom |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `M&A` |
| **State relevance** | CA, CO |
| **Leading indicator** | N — confirmed announcements |
| **Expected volume** | very low (<1/month) |
| **Priority tier** | 3 |
| **Notes** | CommonSpirit formed from Dignity Health (CA) and Catholic Health Initiatives (CO). Large footprint in target states. Network agreement changes here affect CA and CO markets. |

---

## F. State & Regional Government

### Connect for Health Colorado

| Field | Value |
|-------|-------|
| **URL** | https://connectforhealthco.com/about/newsroom/ |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `network` `procurement` — CO ACA marketplace carrier changes |
| **State relevance** | CO |
| **Leading indicator** | Y — carrier participation decisions announced before open enrollment |
| **Expected volume** | very low (seasonal — announcements concentrated May–August) |
| **Priority tier** | 2 |
| **Notes** | CO state-based ACA marketplace equivalent to Covered California. Carrier entry/exit decisions here are significant CO market events. |

---

### Colorado Division of Insurance

| Field | Value |
|-------|-------|
| **URL** | https://doi.colorado.gov/news |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` |
| **State relevance** | CO |
| **Leading indicator** | Y — enforcement actions and plan filings precede public awareness |
| **Expected volume** | very low (<2/month) |
| **Priority tier** | 3 |
| **Notes** | CO state insurance regulator. Similar to CA DMHC but lower volume. |

---

### Nevada Division of Insurance

| Field | Value |
|-------|-------|
| **URL** | https://doi.nv.gov/News/Press_Releases/ |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` |
| **State relevance** | NV |
| **Leading indicator** | Y — enforcement and plan approval actions |
| **Expected volume** | very low (<2/month) |
| **Priority tier** | 3 |
| **Notes** | NV state insurance regulator. Low volume but NV is a target state. |

---

### Missouri Department of Insurance

| Field | Value |
|-------|-------|
| **URL** | https://insurance.mo.gov/consumers/news/ |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` |
| **State relevance** | MO |
| **Leading indicator** | Y — enforcement and plan approval actions |
| **Expected volume** | very low (<2/month) |
| **Priority tier** | 3 |
| **Notes** | MO state insurance regulator. |

---

### Wisconsin Office of the Commissioner of Insurance

| Field | Value |
|-------|-------|
| **URL** | https://oci.wi.gov/Pages/News/Press-Release.aspx |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` |
| **State relevance** | WI |
| **Leading indicator** | Y — enforcement and plan approval actions |
| **Expected volume** | very low (<2/month) |
| **Priority tier** | 3 |
| **Notes** | WI state insurance regulator. |

---

## G. New York / New Jersey State Sources

### New York Department of Financial Services (DFS)

| Field | Value |
|-------|-------|
| **URL** | https://www.dfs.ny.gov/industry/health_insurance |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` `mental-health` `ACA` — plan approvals, enforcement, rate filings, mental health parity |
| **State relevance** | NY |
| **Leading indicator** | Y — NY DFS enforces mental health parity and ACA requirements aggressively; enforcement actions precede public awareness |
| **Expected volume** | low (2–4 items/month) |
| **Priority tier** | 2 |
| **Notes** | NY's primary insurance regulator. NY has strong mental health parity laws — DFS enforcement actions are a useful signal for category 11 (mandated mental health benefits). Rate filings and plan approval notices also signal carrier market entry/exit. |

---

### NY State of Health Marketplace

| Field | Value |
|-------|-------|
| **URL** | https://nystateofhealth.ny.gov/news |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `ACA` `network` `procurement` — NY ACA marketplace carrier participation |
| **State relevance** | NY |
| **Leading indicator** | Y — carrier participation decisions announced before open enrollment |
| **Expected volume** | very low (seasonal) |
| **Priority tier** | 2 |
| **Notes** | NY state-based ACA marketplace. Carrier entry/exit decisions are significant NY market events. Equivalent role to Covered California and Connect for Health Colorado. |

---

### New Jersey Department of Banking and Insurance (DOBI)

| Field | Value |
|-------|-------|
| **URL** | https://www.nj.gov/dobi/ |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `regulatory` `network` `ACA` |
| **State relevance** | NJ |
| **Leading indicator** | Y — enforcement and plan approval actions |
| **Expected volume** | very low (<2/month) |
| **Priority tier** | 3 |
| **Notes** | NJ state insurance regulator. NJ runs its own ACA marketplace (Get Covered NJ). |

---

### Get Covered NJ

| Field | Value |
|-------|-------|
| **URL** | https://www.getcoverednj.gov |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `ACA` `network` `procurement` — NJ ACA marketplace carrier participation |
| **State relevance** | NJ |
| **Leading indicator** | Y — carrier participation decisions |
| **Expected volume** | very low (seasonal) |
| **Priority tier** | 3 |
| **Notes** | NJ state-based ACA marketplace. Lower volume than NY State of Health. |

---

### NY Carrier Newsrooms

The following carriers are dominant in the NY market and worth monitoring for network and M&A announcements:

| Source | URL | Category | Signal Types | Priority |
|--------|-----|----------|--------------|----------|
| Empire BlueCross (Elevance) | https://www.elevancehealth.com/newsroom | Carrier newsroom | `network` `M&A` | 2 |
| Healthfirst | https://healthfirst.org/about-us/news | Carrier newsroom | `network` `M&A` | 3 |
| EmblemHealth | https://www.emblemhealth.com/about/news | Carrier newsroom | `network` `M&A` | 3 |
| Oscar Health | https://www.oscar.com/blog | Carrier newsroom | `network` `ACA` `M&A` | 3 |

> Oscar Health is publicly traded (OSH) and ACA-focused; SEC filings and earnings coverage also signal network strategy changes. Empire BlueCross is the Elevance/Anthem NY subsidiary — its announcements appear on the Elevance newsroom already listed in Section D.

---

## H. National Policy & Regulatory Sources

These sources cover the ACA, federal-to-state funding shifts, and universal healthcare signals (triage categories 1–3, 10, 12, 14–15).

### CMS Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.cms.gov/newsroom |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `ACA` `federal-shift` `regulatory` — federal Medicare/Medicaid/ACA announcements |
| **State relevance** | all — national policy with direct state impact |
| **Leading indicator** | Y — CMS rule changes and waivers affect state markets before they're implemented |
| **Expected volume** | medium (3–5 relevant items/week) |
| **Priority tier** | 2 |
| **Notes** | Center for Medicare and Medicaid Services. CMS newsroom is the primary federal source for ACA marketplace changes, Medicaid waiver approvals, and prior auth rule changes. High volume — filtering to `network`, `ACA`, `federal-shift` tags will reduce noise. |

---

### Medicaid.gov Newsroom

| Field | Value |
|-------|-------|
| **URL** | https://www.medicaid.gov/about-us/news/index.html |
| **Category** | government-regulatory |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `federal-shift` `ACA` `regulatory` — block grant proposals, waivers, federal-to-state funding changes |
| **State relevance** | all — especially CA, NY, NJ which have large Medicaid populations |
| **Leading indicator** | Y — waiver and block grant announcements land here before state-level implementation |
| **Expected volume** | low (1–3 relevant items/week) |
| **Priority tier** | 2 |
| **Notes** | Separate from CMS.gov. Block grant news and 1115 waiver approvals land here first — these are the federal-to-state responsibility shift signals (category 12). |

---

### NAMI Press Room

| Field | Value |
|-------|-------|
| **URL** | https://www.nami.org/press-room |
| **Category** | advocacy / regulatory signal |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `mental-health` — mental health parity enforcement, mandated benefit advocacy |
| **State relevance** | all — national advocacy with state-level action focus |
| **Leading indicator** | Y — NAMI press releases often precede or coincide with state parity enforcement actions |
| **Expected volume** | very low (<1/week relevant) |
| **Priority tier** | 3 |
| **Notes** | National Alliance on Mental Illness. Useful for category 11 (mandated mental health benefits) signals. Low volume. |

---

### Politico Health Care

| Field | Value |
|-------|-------|
| **URL** | https://www.politico.com/health-care |
| **Category** | trade press / policy |
| **Access barrier** | subscription-only (Politico Pro) |
| **Technical complexity** | N/A — blocked without subscription |
| **Signal types** | `ACA` `MFA` `federal-shift` `mental-health` — federal health policy, ACA regulatory changes, federal-to-state funding |
| **State relevance** | all — federal policy with state impact |
| **Leading indicator** | Y — breaks federal health policy stories before they appear in trade press |
| **Expected volume** | high (if subscribed) |
| **Priority tier** | 3 — blocked |
| **Notes** | Politico Pro Health is one of the fastest sources for federal ACA and health policy news. Subscription cost is significant. Awareness only — flag for future consideration if budget allows. |

---

## I. Cost & Market Driver Sources (GLP-1 / PBM)

These sources cover GLP-1 drug costs and PBM/formulary changes that affect carrier plan costs (triage category 13).

### Drug Channels Institute

| Field | Value |
|-------|-------|
| **URL** | https://www.drugchannels.net |
| **RSS** | https://www.drugchannels.net/feeds/posts/default |
| **Category** | industry intelligence / cost driver |
| **Access barrier** | free |
| **Technical complexity** | RSS available |
| **Signal types** | `GLP-1` — PBM formulary decisions, drug pricing, carrier cost impact |
| **State relevance** | all — national PBM/drug pricing analysis |
| **Leading indicator** | Y — Adam Fein's analysis often surfaces formulary and coverage changes before they're widely reported |
| **Expected volume** | low (1–2 relevant posts/week) |
| **Priority tier** | 2 |
| **Notes** | The most authoritative free source on PBM/drug channel economics. GLP-1 formulary decisions by Express Scripts, CVS Caremark, and OptumRx directly affect carrier cost structures. Has RSS. |

---

### Express Scripts / Evernorth Research Blog

| Field | Value |
|-------|-------|
| **URL** | https://www.evernorth.com/articles |
| **Category** | carrier/PBM research |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `GLP-1` — PBM formulary and drug cost research from Cigna's PBM subsidiary |
| **State relevance** | all |
| **Leading indicator** | Y — Evernorth research often pre-announces formulary changes |
| **Expected volume** | very low (<1/week relevant) |
| **Priority tier** | 3 |
| **Notes** | Cigna's PBM and health services subsidiary. Research blog publishes drug spend analysis. Useful context for GLP-1 cost driver signals. Low volume. |

---

## J. Labor & Employer Plan Sources

These sources cover labor union healthcare negotiations and large employer plan changes (triage categories 8, 16).

### SEIU Healthcare Media

| Field | Value |
|-------|-------|
| **URL** | https://www.seiu.org/media |
| **Category** | labor / advocacy |
| **Access barrier** | free |
| **Technical complexity** | plain HTTP |
| **Signal types** | `labor` `TPA` — healthcare worker strikes, contract negotiations, employer plan changes |
| **State relevance** | CA, NY, NJ — largest SEIU Healthcare membership |
| **Leading indicator** | Y — SEIU press releases announce strikes and contract demands weeks before resolution; healthcare coverage terms are always in scope |
| **Expected volume** | low (1–2 relevant items/month) |
| **Priority tier** | 2 |
| **Notes** | SEIU Healthcare is the largest healthcare worker union in the US. Labor contract negotiations at major hospital systems or carriers (e.g., Kaiser Permanente labor disputes) are significant leading indicators of network disruption. |

---

### Employee Benefit News

| Field | Value |
|-------|-------|
| **URL** | https://www.benefitnews.com |
| **RSS** | https://www.benefitnews.com/feed |
| **Category** | trade press / employer plans |
| **Access barrier** | free |
| **Technical complexity** | RSS available |
| **Signal types** | `TPA` `labor` — large employer plan changes, TPA switches, self-funded plan signals |
| **State relevance** | all — national employer benefits coverage |
| **Leading indicator** | Y — reports on large employer plan decisions before they're reflected in carrier results |
| **Expected volume** | low (1–3 relevant articles/week) |
| **Priority tier** | 2 |
| **Notes** | Covers large employer health benefit decisions — self-funded plan shifts, TPA switches, carrier contract changes from the employer side. Useful for category 8 (TPA or administrator switches). Has RSS. |

---

## Quick-Reference Summary

> All target states: CA, NV, CO, MO, WI, NY, NJ

| Source | Tier | Access | Technical | Leading Indicator | Primary States |
|--------|------|--------|-----------|-------------------|----------------|
| Becker's Payer ✓ | — | free | RSS | N | all |
| **Fierce Healthcare** (Payer + Layoff Tracker) | **1** | free | RSS | **Y** | all |
| **Healthcare Dive** (Payers) | **1** | free | RSS | N | all |
| **KFF Health News** | **1** | free | RSS | **Y** | CA, all |
| **CalPERS Newsroom** | **1** | free | plain HTTP | **Y** | CA |
| **DMHC Press Releases** | **1** | free | plain HTTP | **Y** | CA |
| Covered California Newsroom | 2 | free | plain HTTP | **Y** | CA |
| Modern Healthcare (Insurance) | 2 | paywalled | plain HTTP | N | all |
| MedCity News | 2 | free | RSS | N | all |
| STAT News | 2 | partial paywall | RSS | **Y** | all |
| Kaiser Permanente Newsroom | 2 | free | plain HTTP | **Y** | CA, CO |
| Blue Shield CA Newsroom | 2 | free | plain HTTP | N | CA |
| Health Net Newsroom | 2 | free | plain HTTP | N | CA |
| Elevance/Anthem Newsroom | 2 | free | plain HTTP | N | CA, CO, MO, WI, NY |
| UnitedHealth Group Newsroom | 2 | free | plain HTTP | N | all |
| Cigna Newsroom | 2 | free | plain HTTP | N | all |
| Sutter Health Newsroom | 2 | free | plain HTTP | **Y** | CA |
| Intermountain Health Newsroom | 2 | free | plain HTTP | **Y** | CO, NV |
| Connect for Health Colorado | 2 | free | plain HTTP | **Y** | CO |
| NY DFS | 2 | free | plain HTTP | **Y** | NY |
| NY State of Health Marketplace | 2 | free | plain HTTP | **Y** | NY |
| CMS Newsroom | 2 | free | plain HTTP | **Y** | all |
| Medicaid.gov Newsroom | 2 | free | plain HTTP | **Y** | all |
| Drug Channels Institute | 2 | free | RSS | **Y** | all |
| SEIU Healthcare Media | 2 | free | plain HTTP | **Y** | CA, NY, NJ |
| Employee Benefit News | 2 | free | RSS | **Y** | all |
| Empire BlueCross Newsroom | 2 | free | plain HTTP | N | NY |
| Providence Newsroom | 3 | free | plain HTTP | N | CA, NV |
| CommonSpirit Newsroom | 3 | free | plain HTTP | N | CA, CO |
| CO Division of Insurance | 3 | free | plain HTTP | **Y** | CO |
| NV Division of Insurance | 3 | free | plain HTTP | **Y** | NV |
| MO Department of Insurance | 3 | free | plain HTTP | **Y** | MO |
| WI OCI | 3 | free | plain HTTP | **Y** | WI |
| NJ DOBI | 3 | free | plain HTTP | **Y** | NJ |
| Get Covered NJ | 3 | free | plain HTTP | **Y** | NJ |
| Healthfirst Newsroom | 3 | free | plain HTTP | N | NY |
| EmblemHealth Newsroom | 3 | free | plain HTTP | N | NY |
| Oscar Health Blog | 3 | free | plain HTTP | N | NY, NJ |
| AHIP News | 3 | free | plain HTTP | N | all |
| Mark Farrah Associates | 3 | free | plain HTTP | N | all |
| CAHP | 3 | free | plain HTTP | N | CA |
| NAMI Press Room | 3 | free | plain HTTP | **Y** | all |
| Evernorth Research | 3 | free | plain HTTP | **Y** | all |
| AIS Health / Health Plan Weekly | 3 — **blocked** | subscription | N/A | **Y** | all |
| Health Affairs | 3 — **blocked** | paywalled | plain HTTP | N | all |
| Politico Health Care | 3 — **blocked** | subscription | N/A | **Y** | all |

---

## Recommended Scraping Order (for domain expert prioritization)

**Add immediately (Tier 1 — free, high signal, proven technical path):**
1. Fierce Healthcare Payer + Layoff Tracker — RSS, free, direct leading indicator for account team layoffs
2. Healthcare Dive Payers — RSS, free, broad M&A and contract coverage
3. KFF Health News — RSS, free, CA investigative + ACA/federal policy
4. CalPERS Newsroom — plain HTTP, free, direct procurement/RFP signal source
5. DMHC Press Releases — plain HTTP, free, enforcement = relationship strain signal

**Add next (Tier 2 — free, lower volume or new signal categories):**
- CMS and Medicaid.gov newsrooms — for federal-to-state shift signals (categories 3, 12)
- NY DFS and NY State of Health — for NY target state coverage
- Drug Channels Institute — RSS, free, GLP-1 / PBM cost signals (category 13)
- SEIU Healthcare — labor signals (category 16)
- Employee Benefit News — TPA switch signals (category 8)
- Carrier newsrooms: UHG, Cigna, Elevance, Kaiser, Blue Shield CA, Health Net
- Sutter Health, Intermountain Health provider newsrooms
- Covered California, Connect for Health Colorado

**Aware but not actionable now (Tier 3):**
- Paywalled / subscription: Modern Healthcare, AIS Health, Health Affairs, Politico Health Care
- Lower-volume state regulators: CO, NV, MO, WI, NJ
- Trade associations and advocacy: AHIP, CAHP, NAMI (low discovery value)
- Smaller NY carriers: Healthfirst, EmblemHealth, Oscar
