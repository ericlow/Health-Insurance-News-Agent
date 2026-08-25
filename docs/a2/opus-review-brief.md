# Opus Design Review Brief — A2 Analysis Agent

## Who you are reviewing for

Eric Low, executive at Elevance Health (Anthem Blue Cross CA). He is building an on-demand analysis agent for Matt, an account-facing domain expert at Elevance who monitors health insurance market events and presents findings to his customers.

## What has been designed

An on-demand analysis agent (A2) that Matt triggers via Discord when a significant market event occurs. Matt provides an article and a question ("how does this affect Anthem?"). The agent researches the event, pulls primary data, and posts structured findings back to Discord — with every claim tagged by confidence level.

### Documents to read (in this order)

1. `docs/a2/Aug_24_agent_discussion.md` — **most important** — the current state of all design decisions made today; supersedes parts of the TRD
2. `docs/a2/prd.md` — what A2 is and why
3. `docs/a2/trd.md` — formal technical design (partially superseded by the discussion doc)
4. `docs/adr/ADR-003-analysis-agent-tool-design.md` — why generic tools, no program-specific wrappers
5. `docs/adr/ADR-002-compute-platform.md` — why Lambda and stateless architecture

### Primary evidence — understand Matt's actual workflow before reviewing

6. `docs/AGE-71 — CalOptima OC Entry Analysis - Discord conversation.txt` — the original Discord conversation with Matt; read this to understand how Matt thinks, what he caught that the agent missed, what his customers actually want
7. `docs/analysis/age-71-caloptima-oc.md` — the full CalOptima analysis; §0 contains the SB 260 post-mortem which is the origin of the rules layer requirement
8. `docs/A look inside the expanded partnership between SCAN and Costco.txt` — the second test case article; "two unnamed states" drove the conversational model requirement. his current guidance was "I'd start with doing a google search first to understand the implications". he did not give further guidance.

---

## What is settled — do not relitigate these

- **Rules layer:** a curated markdown document (`docs/regulatory-rules.md`) of standing regulatory mechanisms governing member flows. Matt seeds and maintains it. The agent calls `lookup_regulatory_rules` as a mandatory first step before any data pull. This is well-designed and agreed upon.
- **Conversational model:** Matt and the agent iterate; Matt can steer, correct, and provide supplementary context mid-analysis. A finalize step produces a single clean artifact.
- **Confidence tagging:** HIGH (downloaded primary file), MED (web page), LOW (modeled), MECHANISM (statute/rule, no data)
- **Execution:** Lambda + Neon + Discord slash command `/analysis`
- **Conversation identity:** human-readable nickname (e.g., `scan-costco`) + vector search for fuzzy retrieval

---

## The specific concern — this is what the review is for

**The rules layer works. The step after it does not.**

In the current design, after `lookup_regulatory_rules` returns a mechanism and a dataset hint, the agent is expected to call `download_and_parse(url)` with a URL. This is too simple and does not reflect reality.

The rules layer will not always — or even usually — return a direct working URL. It returns knowledge about what data exists and roughly where to find it. The actual path from that hint to usable data could be:

1. **Multi-step web navigation** — agent browses a starting URL, reads a page, follows links, navigates a data portal, eventually finds and downloads a file. Could be 3–5 `browse` calls before reaching the data.

2. **No downloadable file exists** — the relevant data is embedded in a web page (HTML tables, paginated results). The agent reads it directly. Confidence is MED, not HIGH.

3. **Data is not publicly available** — the file is behind a login, a carrier portal, or only accessible through industry contacts. The agent cannot reach it. It must ask Matt.

4. **Matt provides supplementary context** — Matt responds to the agent's question by attaching a file to his Discord message, pasting data, or sharing a URL. The agent reads Matt's attachment and continues.

5. **No structured data exists at all** — the mechanism is real (verifiable in statute), but there is no corresponding dataset. The claim is MECHANISM confidence only.

**Eric's concern:** the current tool design — `lookup_regulatory_rules` followed by `download_and_parse` — implies a clean two-step flow that will rarely be clean in practice. The agent will encounter cases where it needs to navigate, where the data isn't there, and where it needs Matt's help. Is the agent design robust enough to handle this? Will Claude actually navigate these situations well with the tools described, or does the tool design need to be rethought?

**Specific tool in question:** we discussed collapsing `fetch_page` and `download_and_parse` into a single `browse(url)` tool that handles HTML, PDF, and XLSX by content type. Whether this is sufficient — or whether the agent needs more structure — is the open design question.

---

## What we want from this review

A critique of the agent design specifically around the data discovery and retrieval step. Please answer:

1. Given the five scenarios above (navigation, no file, not public, Matt provides it, no data exists), is the current tool set sufficient for the agent to handle each one gracefully?

2. Is `browse(url)` the right abstraction, or does the agent need something different?

3. How should the interaction model handle the case where the agent cannot find data and needs Matt to provide it? Is the current conversational model (Matt responds with attachment or paste) well-integrated into the tool design, or is there a gap?

4. What is missing or underspecified in the current design that will cause the agent to fail in practice?

Be direct. Flag weaknesses. Do not validate what is working — focus on what will break.
