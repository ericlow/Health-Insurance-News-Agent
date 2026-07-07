# Spec-Driven Development Playbook

_Source: "Spec-Driven Production Grade Development in the Age of Vibe Coding" (Lee Boonstra, Google, May 2026) + synthesis with Addy Osmani / Gokul Rajaram frameworks. This is the authoritative SDD reference for this project._

---

## The Core Shift

**Code is now disposable. Specs are the durable asset.**

In agentic development, a developer's primary output is not code — it's the specification that can regenerate that code repeatedly. If you have a rock-solid spec, you can throw away the codebase and rebuild it. You can flip the project from Python to JavaScript in an afternoon. You cannot do this if the knowledge lives in the code.

The bottleneck has moved downstream: AI can write a thousand lines by lunch, but humans still have to review, integrate, and verify. The developer's role is now **technical architect and verifier**, not primary implementor.

> "If a brain is given a 'vibe' instead of a 'blueprint,' it will guess. And in enterprise software, guessing is how Rogue Agent incidents occur." — Lee Boonstra

---

## What Makes a Good Spec

A production-grade spec has **four mandatory components**:

### 1. Full Technical Design
Not just "make a login page." Break it down:
- Functional requirements (what it does)
- Data schemas (how the data is structured)
- API contracts (what interfaces it exposes/consumes)
- Integration points (what it touches)

### 2. Visual Aids
- Diagrams (Mermaid preferred — renderable in Markdown)
- Specific library names with **version numbers** — without versions, the agent defaults to its training cutoff and suggests outdated dependencies

### 3. Background Information — The WHY
This is the most commonly skipped section and the most important for agents. Give the agent:
- Why this feature exists
- What problem it solves
- What constraints shaped the design
- What alternatives were considered and rejected

> "Give the agent the 'Why' behind the 'What.' This will help the agent to think forward — it knows the steps you will likely need as well." — Lee Boonstra

Agents that know the WHY make better decisions when they hit an ambiguous edge case. Without it, they guess. Specs without a WHY section are the primary cause of context fragmentation.

### 4. Scenarios — Behavioral Contracts
What does good look like? What's wrong? What are the edge cases? Written in BDD/Gherkin syntax (see below).

---

## Spec Format: Hybrid Markdown + YAML

A 2026 study (Ouyang et al.) found LLM agents have **up to 40% performance variance** based on spec format alone. The optimal format:

- **Markdown** for narrative text, headers, background, and prose descriptions
- **YAML** for any structured data with nesting depth > 3 (schemas, configs, API contracts)

YAML achieves 51.9% parsing accuracy on nested structures vs. 33.8% for XML and 43.1% for JSON. This is not a stylistic choice — it directly affects agent output quality.

**Rule of thumb:** If you're writing a data structure with more than 3 levels of nesting, switch to YAML.

---

## BDD / Gherkin: The Scenario Format

Behavior-Driven Development (BDD) with Gherkin syntax is the recommended format for behavioral specs. It forces **State → Action → Outcome** thinking, which eliminates vibe and keeps the agent on a strict track.

### Gherkin Template
```gherkin
Scenario: [descriptive name of the behavior being tested]
  Given [the initial state / preconditions]
  When  [the action or event that occurs]
  Then  [the expected outcome]
  And   [additional expected outcomes, if any]
```

### Example (from this project's KFF scraper)
```gherkin
Scenario: Listing page excludes Spanish sidebar articles
  Given a KFF California listing page with articles in aside.term-sidebar
  When _fetch_kff_listing_page is called
  Then no articles with '/es/' in the URL are returned

Scenario: Pagination stops after page limit is reached
  Given a KFF listing page where a.next.page-numbers exists
  When _fetch_kff_listing_page is called and page limit is 3
  Then next_url is returned for pages 1 and 2
  And  next_url is None after page 3 is fetched
```

### Why Gherkin works better than prose acceptance criteria
- Forces you to specify the exact initial state (Given) — exposes hidden assumptions
- Forces a single observable outcome per scenario (Then) — makes tests obvious
- Unambiguous: the agent cannot "vibe" an interpretation
- Each scenario maps directly to one test case

---

## Spec Template

Use this structure for every spec in `docs/specs/`:

```markdown
# [Feature Name] — Feature Spec

_Status: [draft | ready for implementation | implemented]_
_Last updated: YYYY-MM-DD_

---

## Background

[Why does this feature exist? What problem does it solve? What constraints shaped
the design? What was considered and rejected? What business context does the agent
need to make good decisions at the edges?]

---

## User Story

As a [role], I want [capability] so that [business outcome].

---

## Acceptance Criteria

1. [Plain-language criterion 1]
2. [Plain-language criterion 2]

---

## Technical Design

### Data Model / Schema
[Tables, fields, types — use YAML for nested structures]

### API Contracts
[Endpoints, inputs, outputs — use YAML]

### Selectors / Integration Points
[CSS selectors, external API endpoints, file paths, etc.]

---

## Behavioral Specs (Gherkin)

### [Component 1 Name]

```gherkin
Scenario: [happy path]
  Given ...
  When  ...
  Then  ...

Scenario: [edge case]
  Given ...
  When  ...
  Then  ...
```

### [Component 2 Name]
...

---

## Decisions

| Question | Decision | Rationale |
|---|---|---|
| [open question] | [chosen answer] | [why] |

---

## Out of Scope

- [Thing 1 — explicitly excluded and why]
```

---

## Where Instructions Live: The 3-Tier Model

| Tier | Location | What goes here |
|---|---|---|
| **System prompt** | `CLAUDE.md`, `AGENTS.md` | Agent identity, hard rules, workflow philosophy — loaded every session |
| **Specs** | `docs/specs/*.md` | Task-specific technical designs, BDD scenarios, schemas — loaded per task |
| **Skills** | `.claude/commands/*.md` | Reusable procedural workflows triggered on demand |
| **Chat** | IDE chat / terminal | Ephemeral high-level orchestration only — never primary spec location |

**Never dump a 100-page spec into chat.** It exhausts the short-term context budget, increases latency, and fragments context. The specs folder is static context that the agent indexes; chat is for orchestration.

---

## Execution Modes

Different tasks need different prompting postures:

### Architect Mode (new project / new component)
- Prompt the agent to **propose structure first, not code** — confirm folder layout and tech stack before any implementation
- Include test generation, documentation, and logging in the initial prompt
- Always include library version numbers

### Builder Mode (feature on existing codebase)
- Prompt the agent to match existing style: naming patterns, error handling conventions
- When multiple files change, confirm each diff before moving to the next
- Reference the relevant spec file explicitly: `"Implement the scenarios in docs/specs/foo.md"`

### Forensic Mode (bug fixing)
- Shift from symptom prompting (`"the button doesn't work"`) to evidence prompting (`"logs show 403 on POST /api/foo"`)
- **Always prompt for a failing test that reproduces the bug first** — before any fix
- Set a strict constraint: only fix the root cause; do not clean up unrelated code
- Keep the reproduction test in the codebase permanently

### Author Mode (documentation)
- Documentation is the source of truth; if docs and code diverge, the agent hallucinates
- README.md and CHANGELOG.md must always stay in sync with code changes
- Use Google Style Docstrings (Python) or JSDoc (TypeScript)

### Librarian Mode (data / SQL)
- Always prompt the agent to show the specific SQL query used to generate output
- Treat schema changes as first-class spec items

---

## Test-First Discipline

In SDD, the test is the contract. Before any implementation:

1. **Write a failing test** (or a failing curl command) that reproduces the expected behavior
2. Implementation must make that test pass
3. The test stays in the codebase permanently — it is a regression guard

This turns "write code" into "make this test pass" — a far tighter, verifiable directive.

---

## Anti-Patterns

| Anti-pattern | What goes wrong | Fix |
|---|---|---|
| Vibe spec ("make a login page") | Agent guesses; generates plausible-but-wrong implementation | Write full technical design with schemas and scenarios |
| Missing WHY | Agent makes wrong decisions at edge cases; comprehension debt compounds | Always include Background section |
| No version numbers | Agent defaults to training-cutoff versions of libraries | Pin all library versions in spec |
| Spec in chat | Context lost between sessions; agent can't reference it | Always commit spec to `docs/specs/` before implementation |
| Giant PRs | Review gridlock; merge conflicts multiply | One spec = one branch = one PR, lifetime ≤ 1 day |
| Cleanup in bug fix | Complicates review; hides root cause fix | Strictly constrain agent: fix only the root cause |
| Spec written after code | Code becomes the spec; WHY is lost; agent infers intent incorrectly | Write spec first, always |

---

## The Economics Argument (for convincing stakeholders)

**Vibe coding:** Low upfront cost, high ongoing cost. Every bug requires reverse-engineering AI-generated code. Security fixes in production cost exponentially more than design-phase catches.

**Agentic engineering (SDD):** Higher upfront spec investment, dramatically lower marginal cost per feature. AI operates within a governed factory; output is structurally sound, pre-tested, and aligned with standards.

Context engineering (structured specs) is a **financial strategy**, not just a technical one. Every token you send to the agent costs money. A tight spec with high-signal context dramatically increases first-pass success rate, eliminating the expensive trial-and-error loops of vibe coding.

---

## Connection to This Project's Existing Process

This project already practices SDD. The current process in `CLAUDE.md` maps to the Day 5 framework as follows:

| This project | Day 5 framework |
|---|---|
| `docs/prd.md` | Business context / problem statement |
| `docs/technical-design.md` | Architectural north star |
| `docs/specs/*.md` | Task-specific BDD specs |
| `docs/inputs.md` | Domain expert context (feeds Background sections) |
| Linear issues with acceptance criteria | Gherkin scenarios (opportunity to upgrade) |
| Feature branches ≤ 1 day | Enforces disposable-code mindset |

**Gaps to close:**
1. Specs are missing **Background/WHY sections** — add to every spec
2. Acceptance criteria are prose bullets — **upgrade to Gherkin Scenario/Given/When/Then**
3. Specs don't pin **library version numbers**
4. No formal **failing-test-first discipline** in the workflow

---

## Quick Reference: Coaching Checklist

When reviewing a spec before implementation, verify:

- [ ] Background section exists and explains WHY, not just WHAT
- [ ] User story is present
- [ ] Scenarios are in Gherkin format (or at minimum, clearly Given/When/Then)
- [ ] Happy path scenario exists
- [ ] At least one edge case / failure scenario exists
- [ ] Library versions are pinned
- [ ] Decisions table documents open questions and their resolution
- [ ] Out of scope section is explicit
- [ ] Spec is committed to `docs/specs/` before implementation begins
- [ ] A failing test exists (or is the first implementation step)
