# Domain Expert Inputs

---

## 2026-06-19

We are looking for major changes in relationships. Could be the form of acquisitions, mergers, partnerships, divestitures, or terminations of deals between major insurance carriers and providers.

Time frame would be last five years; shorter is also fine.

What I need to do for the agent is figure out how to give it a goal once it finds something. Right now, I'm thinking: define geographic regions impacted, size the entities involved economically, and perhaps do research on alternatives.

In essence, the agent that we are building will prompt other agents.

**Example — CalPERS/United/Sutter:**

CalPERS prepares to drop United Healthcare. ~90k members shifting from United to Sutter. Sutter is not a full-blown insurance carrier. Anthem is actually the third party that processed the claims — so Anthem also wins. And Sutter needs to fill out the network and they are using Anthem's network to do that — another win for Anthem.

Two telltale signs this was coming: (1) CalPERS said they want to kick out United and opened a soft RFP. (2) United laid off the CalPERS sales team a month ago.

In this case, this is huge news, but not necessarily my rodeo. What I would want to show is how much volume was picked up via Sutter.

References:
- https://newsroom.cigna.com/uc-health
- https://www.yahoo.com/healthcare/articles/calpers-prepares-drop-united-healthcare-000333348.html

---

## 2026-06-20

Build in two phases:

1. First build the system that pulls news items from the source and saves them to the database.
2. Then design the prompts that analyze and triage the saved articles — to extract details, determine if they are financial or not, etc.

We care about three types of substantive stories: (1) relationship changes, (2) business changes, and (3) financial implications. The triage filter should discard generic PR content and soft qualitative stories — both types are noise. Stories need to be about actual relationships, business events, or financial impact to be worth analyzing further.

All articles sourced from newsroom.cigna.com are public information — no data privacy constraints on tooling choices.

Use Braintrust for prompt testing and evaluation. Articles are public so there is no concern with sending them to a commercial platform.

## 2026-07-10

Another input
https://med.stanford.edu/news/all-news/2021/02/stanford-medicine-and-sutter-health-to-provide-east-bay-cancer-care.html

https://med.stanford.edu/news/all-news/2026/04/st-rose-stanford-collaboration.html

## 2026-07-11

**Short list of entities to watch:**

Insurers: United Healthcare, Blue Shield, Anthem / Blue Cross, Aetna, Cigna, Healthnet / Centene, Kaiser

Hospitals / doctors: Sutter Health, Stanford, UC, Cedars, Providence, Optumcare, Heritage, Scripps, Sharp, Kaiser

Employers: CalPERS, nursing unions, doctors unions, labor unions for major employers

California Health and Human Services open data portal: https://data.chhs.ca.gov/

## 2026-07-11 — Agentic system design brainstorm

# Health Insurance News Bot — Agentic System Design

## Project Context

Building a news scraping app for health insurance financial news (contracts, deals,
terminations, mergers, reinsurance, rate filings, litigation with financial exposure).
Sources are scraped into Postgres. Domain expert is a health insurance executive who
wants alerts on financially material news, delivered via Discord.

A separate dedup pipeline exists as a concept (entity fingerprinting + LLM-as-judge)
but is **unvalidated** — treat clustering as unreliable until tested. Agentic
capabilities below should not hard-depend on dedup working.

## Goals

1. Deliver real value to the health insurance exec (fast, trustworthy, low-noise alerts
   and answers).
2. Build learning reps in agentic system design: tool use, orchestration, grounding,
   human-in-the-loop feedback.

## System Shape: Single Discord Bot, Shared Toolset

**Passive/push side** — background loop, always running:
scraper → dedup (once validated) → triage/relevance agent → bot posts alert to channel.

**Active/pull side** — exec interacts via open mentions (not slash commands):
exec @-mentions bot in natural language → bot orchestrates tools → responds with
cited, grounded answer.

Chosen: **open mentions** over slash commands, despite higher hallucination risk,
because it's more natural for the exec.

## Tools Available to the Conversational Agent

- `summarize_article(url_or_id)` — single-article brief (build first, no dedup dependency)
- `summarize_cluster(cluster_id)` — multi-article synthesis, reconciles conflicting
  figures across sources (build only after dedup is validated — bad clusters produce
  confidently wrong summaries)
- `query_articles(company, date_range, event_type)` — structured Postgres lookup
- `get_financial_context(company)` — SEC EDGAR filings / stock data via structured
  APIs (not scraping); depends on entity resolution (see Shared Dependency below)
- `search_web(query)` — bounded, only when local data is insufficient
- `record_feedback(alert_id, thumbs_up_or_down)` — closes the loop for triage tuning

## Shared Dependency: Entity Resolution

Company name normalization (e.g. "AIG" vs "American International Group" vs
subsidiary names) is required by dedup, `get_financial_context`, and the
conversational agent's grounding. Build this lookup table/service once, reuse
everywhere — don't solve it three separate times.

## Query Routing Logic

Two-step process per exec question:
1. **Classify** what's being asked (summary request / structured lookup / financial
   context / trend analysis / research question).
2. **Route** to the appropriate tool(s) based on classification, preferring local
   Postgres data first (fast, grounded) and only branching to web search or financial
   APIs when local data is empty or the exec explicitly asks for something outside
   scraped scope.

If the bot lacks sufficient data to answer, it should say so explicitly rather than
hallucinate.

## Hallucination Mitigation: Three-Agent Pipeline

Settled design after discussion — three distinct models/steps so no single model's
errors get reinforced unchecked:

| Step | Role | Model | Rationale |
|---|---|---|---|
| 1. Plan | Interpret the exec's question, output a structured plan of what to fetch | **Opus 4.8** | Handles ambiguity well; planning mistakes cascade through the whole system, so this is the highest-stakes step |
| 2. Execute | Run the tools per the plan (DB query, API calls, web search) | **Haiku 4.5** | Mechanical, low-reasoning task once the plan is set; cheap and fast |
| 3. Interpret | Analyze retrieved data, reconcile conflicting sources, decide relevance, synthesize final response with citations | **Fable 5** | Cost is not a constraint for this project; use strongest available judgment here to catch subtleties/conflicts a cheaper model might miss |

Note on tradeoffs discussed: using the same model for multiple steps risks the system
"agreeing with itself" — a bad plan gets executed and interpreted without correction.
Using three distinct models avoids this. Main known tradeoff of the current design:
sequential calls across three models add latency (roughly 10-20s) — acceptable given
cost is not a constraint for this project, but worth monitoring once real usage starts.

## Build Sequencing (agreed order)

1. **Triage/relevance agent** — single-article scoring against financial materiality
   criteria. No dedup dependency. Build first.
2. **Feedback-loop agent** — store exec's thumbs up/down reactions, periodically have
   an agent review disagreements and propose (not auto-apply) updated relevance
   criteria. Also surfaces dedup-quality signal for free.
3. **Research/enrichment agent** (`get_financial_context`, `search_web`) — structured
   APIs first (SEC EDGAR, stock data), bounded scope, firm stopping conditions to
   avoid rabbit holes.
4. **Event-cluster summarizer** — gated on dedup validation.
5. **Cross-event trend agent** — needs both validated dedup and weeks of historical
   clustered data; most vague success criterion, build last.

Discord bot build order: push-only alerts (triage + single-article summarizer) first
→ pull side (open-mention tool orchestration, three-agent pipeline) once stable.

## Open Items / Not Yet Decided

- Concrete rubric for "why this matters to a health insurer" (candidate categories:
  reserve/capital impact, competitive positioning, regulatory exposure, claims cost
  trend) — needs to be defined so the summarizer isn't freelancing.
- Dedup validation has not been done yet — recommended approach was a small hand-labeled
  test set (20-30 articles) to check entity-fingerprinting precision before building
  anything that depends on clusters.
- Financial-data trigger policy: gate `get_financial_context` behind triage score or
  make it on-demand only, rather than auto-enriching every alert.

## 2026-07-23 — CalOptima OC ACA entry

**Source:** https://www.beckerspayer.com/payer/aca/caloptima-to-be-californias-only-new-aca-carrier-in-2027/

CalOptima Health, the public Medi-Cal insurer for Orange County, Calif., will soon begin selling individual plans on the state's ACA marketplace, Covered California, for the 2027 plan year.

CalOptima will offer coverage in Orange County and is the only new carrier on the state marketplace, according to a July 21 news release. Its entry coincides with Molina Healthcare's exit from the northeastern portion of Los Angeles County and Orange County. Molina's roughly 1,600 enrollees in those areas will be shifted to a new plan or the lowest-cost option in their metal tier.

In total, 12 insurers will offer coverage across California next year. Insurers proposed a preliminary weighted average rate increase of 9.9%, below the preliminary national median of 14%.

CalOptima first told Becker's it planned to join the marketplace in February 2025, pointing to continuity of care for members who cycle in and out of Medi-Cal eligibility as their incomes fluctuate. The new plan, CalOptima Health Covered, will be the lowest-cost Silver plan available in Orange County, the insurer said.

"Our single goal in going on the exchange is to work with that population to offer them affordable access to care and continuity," CEO Michael Hunn previously said. The insurer estimated the offering would reach more than 15,000 people.

**Analysis questions (Eric):**

CalOptima is moving into OC. I want an analysis of how many members they will get and how many I, Elevance, will lose. Also estimate if that impacts the small and individual risk adjustment pool.

## 2026-07-23 — SB 260 missed in AGE-71 analysis

**Eric (verbatim):**

> sb-260 was missed in the analysis. what class of context is missing? why? why is this important.

> the exec is upset that you missed sb260 explain how and why this was missed. update the analysis. summarize the changes between new and old analysis

**Spec impact:** AGE-71 analysis revised (rev 3) to incorporate SB 260 auto-enrollment. AGE-68 (A2 spec) gains a hard requirement: a curated regulatory-mechanism knowledge base ("rules layer") — standing statutes governing member flows cannot be surfaced by news or dataset retrieval and must be maintained as domain memory seeded by expert input.

## 2026-07-29 Meeting with Matt
Feedback from customers of Matt. 

The Cal Optima news and analysis was not highly valued to the particular team. They only care about the personell changes. The analysis was overwhelming to them and they did not even know what to do with it.  Matt had this boiled down to 5 bullet points, but this was still too much. 

Possibly this could be used down the line during negotiations, but at this time, the return on investment is about information exchange. In this case, the customer team only cared about staffing changes.