# Product Requirements Document — Analysis Agent (A2)

_Last updated: 2026-08-23_

---

## 1. Problem Statement

When a significant health insurance market event occurs — a new carrier entering a market, a partnership forming, a contract terminating — understanding what it means for Elevance requires hours of research: finding the right enrollment datasets, knowing which regulatory mechanisms govern member flows, sizing the dollar exposure. That work currently falls on domain experts like Matt, who do it manually and inconsistently.

The A1 pipeline flags events. A2 answers the question that comes next: **what does this mean for Anthem's book?**

---

## 2. Users

**Primary user: Matt**
- Account-facing role at Elevance; presents to his customers (sales/account management teams)
- Interacts via Discord
- Domain expert — catches regulatory gaps, has C-suite contacts at adjacent carriers
- His customers care about personnel implications and market shifts, not financial modeling for its own sake
- Wants an analysis he can trust and act on within minutes of asking, not hours

**Secondary user: Eric**
- Building and operating the system
- Also a consumer of the analysis output

---

## 3. What A2 Is

An on-demand analysis agent that Matt triggers via Discord. Matt provides a news event (article URL or pasted text) and a question. The agent researches the event, pulls primary data, consults a regulatory knowledge base, models the impact, and posts structured findings back to Discord — with every claim tagged by confidence level.

A2 is **not** part of the automated A1 pipeline. It runs only when Matt asks.

---

## 4. Trigger Format

Matt sends two things:

1. **Article** — a URL or pasted article text describing the event
2. **Question** — what he wants to know about it

**v1 optimizes for:** "how does this affect Anthem?"

The question can be anything. Examples:
- "how does this affect Anthem's OC book?"
- "what's Anthem's MA exposure if SCAN launches in CA and NV?"
- "is this a threat to our Medi-Cal contract in LA County?"

The agent's standing context (Elevance perspective, 7 target states) is encoded in its system prompt — Matt doesn't repeat it every time.

---

## 5. Target States and Programs

The agent is scoped to events affecting Elevance's book in:

**States:** CA, NV, CO, MO, WI, NY, NJ

**Programs:**
- ACA individual market (Covered CA in CA; state or federal exchange elsewhere)
- Medicaid managed care (Medi-Cal in CA; state equivalents elsewhere)
- Medicare Advantage
- Commercial fully-insured (large and small group)

National-level events that affect these states are in scope even if the states aren't named directly in the article.

---

## 6. Interaction Model

A2 is a **collaborative conversation**, not a single-shot function. Matt can steer the analysis at any point.

- If the agent hits an information gap it can't resolve (e.g., article says "two unnamed states"), it surfaces the question to Matt and continues with what it has
- Matt can reply with additional context at any point, and the agent incorporates it and continues
- Matt acts as the critic and validator in v1 — he reads the findings, pushes back where wrong, and the agent adjusts

This model is intentional: Matt's real-time domain judgment filling gaps is more reliable than any automated fallback.

---

## 7. Output

Structured findings posted to Discord, containing:

- **What happened** — 2–3 sentence summary of the event
- **Mechanism** — which regulatory or market mechanism drives member movement (e.g., SB 260 auto-enrollment, MA plan switching at open enrollment)
- **Member impact** — estimated members at risk for Anthem, with scenario range
- **Dollar exposure** — estimated gross premium impact
- **Confidence tags** — every claim tagged HIGH / MED / LOW based on how it was sourced
- **Citations** — source reference for each claim

Output is sized for Matt's workflow: structured enough to act on, brief enough to share with his customers (3–4 key facts, not scenario tables).

---

## 8. Success Criteria

1. Matt can trigger an analysis from Discord and receive findings within a reasonable time (target: under 10 minutes for a well-defined event)
2. Every HIGH-confidence claim is traceable to a primary source file the agent downloaded and parsed directly
3. The SB 260 class of miss does not recur — standing regulatory mechanisms are consulted before any data pull
4. Matt can steer the analysis mid-conversation and the agent incorporates his input without restarting from scratch
5. Matt trusts the output enough to share it with his customers without manually verifying every number

---

## 9. Out of Scope (v1)

- Automated triggering — A2 runs only when Matt asks; it does not watch A1's output and self-trigger
- Automated critic layer — Matt is the critic; no automated validation of findings
- Non-Anthem perspective — analysis always frames impact from Elevance's point of view
- States outside the 7 targets — unless a national event has clear downstream effects on the target states
- Scheduled or recurring analysis — A2 is on-demand only

---

## 10. Open Questions

| # | Question | Status |
|---|----------|--------|
| Q1 | Which Discord channel does A2 post to? | Deferred — follows existing channel routing pattern |
| Q2 | Pre-cache enrollment datasets vs. fetch on demand? | Deferred — fetch on demand first; add caching if latency is a problem |
| Q3 | How does Matt authenticate / invoke A2? (Discord bot command, mention, keyword?) | Deferred — define when Discord bot integration is built |
