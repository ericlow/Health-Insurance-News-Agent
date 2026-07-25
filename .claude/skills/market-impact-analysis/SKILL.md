---
name: market-impact-analysis
description: Run an executive-grade market impact analysis of a health insurance industry event (carrier entry/exit, M&A, network change) with anti-hallucination rigor — per-claim citations, confidence levels, primary-source verification, a regulatory rules-layer check, and scenario modeling. Use when Eric asks to analyze the member/financial impact of an industry event, or references a Linear analysis issue. Reference implementation: docs/analysis/age-71-caloptima-oc.md (AGE-71).
---

# Market Impact Analysis

Playbook distilled from AGE-71 (CalOptima's 2027 Covered California entry). Frame every analysis from **Elevance/Anthem's perspective** — Eric is the industry analyst there.

## Workflow

### 1. Intake
- Log the triggering article/input **verbatim** in `docs/inputs.md` (dated entry, never paraphrased), including Eric's questions.
- Confirm or create the Linear issue (Agents team, Health Insurance News Agent project); create the branch from Linear's auto-generated name. Move issue to In Progress when work starts.

### 2. Plan before pulling
Write down: the questions, the data needed per question, and the method. Share the plan with Eric (and to Discord **only with explicit approval** — see §6). State expected weak spots up front (e.g., "if X data isn't public, the base case leans on the claimant's own figure with wide bands").

### 3. Data pulls — primary sources first
- Prefer **downloadable machine-readable primaries** (XLSX/PDF) parsed directly with openpyxl/pypdf over web pages, and web pages over search snippets. Search-snippet numbers are NOT publishable — AGE-71's snippet-sourced RA figure was wrong ($438.8M vs the real $435.08M).
- Known primary sources for this domain:
  - **Covered CA Active Member Profile** (hbex.coveredca.com/data-research/) — enrollment by issuer × rating region × metal tier. Orange County = region 18. Anthem's plan-level rows are region-UNSPECIFIED (known file quirk) — impute from statewide mix and flag it.
  - **CMS RA reports + appendices** (cms.gov premium-stabilization-programs page) — Appendix C = issuer-level individual/small-group transfers; the summary PDF Table 3 = state pool sizes. Use CMS when DMHC PDFs 403-block (they do, even with UA spoofing) — same data, different aggregation.
  - **Covered CA SB-260 Lowest Cost Silver Plan by County PDF** — who holds each county's auto-enrollment default slot.
  - Rate announcements: coveredca.com newsroom; acasignups.net for by-carrier tables.
- Record for every source: retrieval method, verification status (e.g., "totals reconcile to sheet grand total"), reliability tier.

### 4. Rules layer — MANDATORY (the SB 260 lesson)
Before modeling, explicitly ask: **"Which standing statutes and program mechanics govern this member/money flow?"** News and dataset retrieval structurally cannot surface standing law — a 2019 statute makes no 2026 headlines. Checklist of known mechanisms:
- **SB 260**: Covered CA auto-enrolls Medi-Cal leavers into the county's lowest-cost Silver plan (or their same managed care plan); activation = paying first premium. Whoever holds lowest-cost Silver owns the churn acquisition channel *by law*.
- **APTC benchmark**: subsidies peg to the 2nd-lowest-cost Silver; a cheaper entrant raises every incumbent's *net* premiums without touching gross rates.
- **Risk adjustment**: statewide, separate individual and small-group pools; new entrants code thin (low year-1 risk scores) and typically pay in; losing healthy members *reduces* a payer's transfer obligation.
- Molina-style exits: displaced members default-crosswalk to the lowest-cost same-metal plan.
Also read strategy through this lens: a carrier's "continuity of care" positioning may be a statutory default-capture play, not marketing.

### 5. Modeling and the report
- Scenarios: low/base/high with named components; **all scenario outputs are LOW confidence by construction**.
- Model asymmetries honestly (e.g., effectuation rates differ by carrier when continuity of providers differs).
- Distinguish **visible book loss** from **forgone inflow vs. counterfactual** — the second is the silent killer and executives need both framings.
- Report template (see `docs/analysis/age-71-caloptima-oc.md`): confidence key → process notes → method → sources table w/ verification status → market baseline → per-question scenario tables with per-claim `[S#, confidence]` tags → assumptions register with sensitivity ratings → known gaps → A2-automation postscript → revision log.
- Confidence scale: **HIGH** = parsed the primary file myself; **MEDIUM** = fetched page (AI-summarized) or secondary source; **LOW** = analyst judgment. Never present a snippet-sourced number as HIGH.
- **Executive prose standard (TL;DR and Discord posts):** one idea per sentence; no analyst jargon up top — "counterfactual," "effectuation," "severed inflow" belong in the body, not the summary. State a loss in three plain sentences: the visible loss (members who switch), the invisible loss (growth that stops arriving), then the combined total phrased as "ends [year] X members smaller than it would have been." If a summary sentence needs a second read, rewrite it. (AGE-71 rev 4's TL;DR failed this test and had to be reworded.)
- When Eric flags an error or missing context: log his input verbatim in `docs/inputs.md`, fix the report as a new revision with a revision-log entry that names what was wrong, and check whether the lesson belongs in this skill or the A2 spec (AGE-68).

### 6. Delivery protocol
- Commit revisions to the feature branch as they land.
- **Discord (executive webhook): never post without Eric's explicit go-ahead for that specific post.** Hard 2000-char limit per message — split long posts into (1/2), (2/2). Corrections lead with a direct apology and the corrected numbers, then the process fix.
- Merging: follow the repo default (PR to `main`) unless Eric explicitly says "merge and push, no PR" for *this* deliverable — that instruction is per-deliverable, never standing. After merge, post the GitHub blob link on main to Discord (with approval) and mark the Linear issue Done.
- **Git hygiene for merges:** run merge/push as `git -C <primary-repo-path> ...` — a shell whose cwd sits inside a `.claude/worktrees/` worktree will silently switch *that worktree* to main instead of the primary checkout. If a worktree was touched, restore it to its branch and verify with `git worktree list`.
- If the analysis has a known future data release (e.g., final rates in fall), offer a scheduled re-analysis reminder.
