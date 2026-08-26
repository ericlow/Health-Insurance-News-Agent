# Working Session — 2026-08-25

---

## How to resume this later (where everything lives)

Coming back cold? Read in this order:

1. **This file** — current status, outstanding work, and the AWS deployment narrative below.
2. **`docs/specs/2026-08-25-analysis-agent-a2.md`** — the AnalystAgent spec: what it is,
   every design decision + rationale, Gherkin scenarios, what's V1 vs deferred.
3. **`docs/a2/`** — the design *discussion* history behind the spec (`Aug_24_agent_discussion.md`
   has the decisions and the two still-open questions; `trd.md`/`prd.md` the fuller design;
   `live-simulation-aug24.md` the CalOptima dry-run; `opus-review-brief.md` the review).
4. **`infra/analyst/README.md`** — how to redeploy code + infra, and the Discord setup.
5. **Code:** `agent/analyst/` (handler + command registration), `tests/test_analyst_interactions.py`.
   **Infra:** `infra/analyst/` (Terraform). **History:** PRs #44 (stub), #45 (Terraform).
6. **Assistant memory** `project-lambda-url-block` — the Function-URL-blocked lesson (loads
   automatically in a new session).

That set is enough to reconstruct both *what we built* and *why*. The one thing not in git:
live secrets/IDs (`.env`, gitignored) — Discord app ID, bot token, guild ID. Recoverable from
the Discord Developer Portal if lost. The endpoint URL is a Terraform output (reproducible).

---

## Outstanding work — pick up here next session

1. **AnalystAgent real engine** (create AGE-95) — replace the stub with the deferred
   (type 5) + Claude tool-loop flow per `docs/specs/2026-08-25-analysis-agent-a2.md`.
   The walking skeleton is live; this is where the actual analysis work begins.
2. **Doc rename sweep: A2 → AnalystAgent** — code says `analyst`, docs still say "A2"
   (`docs/a2/`, the spec filename, TRD/PRD). Dedicated pass, deferred.
3. **ADR-004 (execution model)** — capture when building the real engine, not before
   (the two-Lambda/deferred model isn't settled yet).
4. **Eric pending:** delete the 1am EventBridge rule (still pending, see below).
5. **Eric pending:** rotate the Jina API key (was shared in chat).
6. **Prior carry-overs:** A1 spec review (`docs/specs/2026-07-19-event-tracking-agent-a1.md`),
   update TDD/PRD to reflect Lambda/Neon/A1/AnalystAgent, merge AGE-70 PR.

---

## Next spec — the engine + research behavior (DECIDE HERE, then write)

Where we left off: individual tools are now spec'd — `fetch_url`
(`docs/specs/2026-08-25-analysis-agent-a2.md`) and `search_web`
(`docs/specs/2026-08-25-analyst-search-web.md`, Jina). The next spec is **not another
tool.**

**Key insight — the research workflow is emergent behavior, not a component.**
"Do a search → explore the hit results → summarize → analyze" is simply what the agent
*does* once the engine runs the Claude tool-loop with `fetch_url` + `search_web` in it:

```
search_web("...")  →  read the 5 snippets  →  fetch_url on the 2-3 promising ones
  →  read those bodies  →  synthesize a confidence-tagged analysis
```

Nobody codes that sequence — Opus decides it turn by turn. So there's no "workflow"
component to build; there are two things left to spec:

1. **The engine (AGE-95)** — the tool-loop machinery: deferred Discord response
   (type 5) + run the Opus loop + save conversation state to Neon. This is the
   prerequisite; nothing runs without it, and it's the biggest remaining piece. Much of
   it is already described in the AnalystAgent V1 spec — the engine spec may just be its
   implementation plan or a thin extension.
2. **The system prompt** — what makes the research *good* vs. flailing: how to phrase
   searches, how many hits to explore, when to stop, weighting primary sources over
   blogs, confidence tagging, and when to ask Matt.

**Open decision to make first next session:** fold the "search/explore/summarize/
analyze" research behavior *into* the engine spec (as its Gherkin acceptance criteria +
a system-prompt section), or pull it out as a standalone "research behavior" spec?
- **Recommendation:** fold it into the engine spec. Write the workflow as Gherkin
  ("given an event with no URL, the agent searches, fetches the top hits, and produces a
  tagged analysis") plus the system-prompt section. The behavior rides on the machinery
  that executes it, so keeping them in one spec avoids drift.

---

## AnalystAgent — walking skeleton LIVE (2026-08-25)

`/analysis` works end-to-end: Discord → API Gateway → Lambda → response
("🟢 A2 stub is alive").

- **Spec:** `docs/specs/2026-08-25-analysis-agent-a2.md` (ready for implementation)
- **Code:** `agent/analyst/interactions.py` (stub handler), `register_commands.py`;
  `tests/test_analyst_interactions.py` (4 pass)
- **Infra:** `infra/analyst/` Terraform (API Gateway → `analyst-handler` Lambda) —
  see `infra/analyst/README.md` for deploy steps
- **Discord app:** AgentAnalyst; endpoint `https://6scddpumv6.execute-api.us-west-1.amazonaws.com/`
- **Key lesson:** Lambda Function URLs are 403-blocked in this account → use API
  Gateway (memory: `project-lambda-url-block`)
- **PRs merged:** #44 (stub), #45 (Terraform)
- **Deferred from V1:** rules layer, `search_web`/`search_articles`, deferred-response
  pattern, Neon conversation state — all part of the real engine (AGE-95)

---

## AWS deployment — what happened (the whirlwind, explained)

Getting `/analysis` from "registered command" to "actually responds" took several
detours. Here's the full story so it makes sense in hindsight.

### The plan
Make the Lambda reachable from Discord. Discord pushes an HTTP POST to a public URL
when a command runs, so we needed (a) the code on a Lambda and (b) a public HTTPS
endpoint. To avoid needing new AWS permissions, we split the work: **create the
function shell in the console** (needs privileges Eric has as root) and **push the
code via CLI** (`update-function-code`, which the existing `.env` key already had).

### Detour 1 — Discord command registration 403
Registering `/analysis` failed with 403. Cause: the bot existed but **wasn't in the
server** (the OAuth2 invite hadn't been completed). Diagnosis: `GET /users/@me/guilds`
returned an empty list. Fix: opened the bot invite URL, added it to the server,
re-ran registration → 201 Created.

### Detour 2 — packaging PyNaCl for Lambda
The signature-verification library **PyNaCl has a compiled C extension**. Installed on
a Mac, its binary won't run on Lambda (Amazon Linux) — it fails at import. Fix: built
the zip with the Linux wheel explicitly (`pip install --platform manylinux2014_x86_64
--only-binary=:all: --python-version 3.12`). Verified the native `_sodium*.so` was in
the package before shipping. (This is documented in `infra/analyst/README.md`.)

### Surprise — the CLI key could do more than expected
CLAUDE.md said the key was update-code-only. In practice it could also set function
config, env vars, create a Function URL, and add resource permissions. So most
provisioning happened over CLI without console clicking.

### Detour 3 — the Function URL 403 that wasn't our code (the big one)
We first tried a **Lambda Function URL** (simpler than API Gateway — one fewer moving
part). Set auth type NONE, added a public-invoke permission. But every request to the
URL returned **403 from AWS's auth layer**, before our handler ran. Waiting for
propagation didn't help.

**Diagnosis:** we invoked the Lambda *directly* (`aws lambda invoke`, bypassing the
URL) with a synthetic event. It returned our handler's correct `401 invalid request
signature` — proving the **code and PyNaCl were fine**, and the block was purely the
URL's auth layer. (This "invoke directly to isolate code from endpoint" trick is the
key diagnostic.)

**Hypothesis chase:**
- Guessed an AWS Organizations SCP (policy blocking public Lambda URLs). But the
  Organizations console showed **no org exists** ("Create an organization") — so not
  an SCP.
- Conclusion: the account has **Lambda block-public-access enabled** — AWS turns this
  on by default for accounts that never used public Function URLs (this account only
  ran the monitor, which uses EventBridge, no URLs). It's not toggleable via the
  installed CLI.

### Resolution — pivot to API Gateway
API Gateway is public and **not subject to the Function-URL block** — and it's what
the spec called for originally. But the existing key lacked API Gateway permissions.

We chose to do this via **Terraform** (reproducible infra-as-code) rather than more
CLI commands. Established the division of labor: **infra = Terraform (run
occasionally); code deploys = GitHub Actions `update-function-code` (per merge)** —
do *not* put `terraform apply` in the per-merge pipeline (it would need create-level
creds in CI for no benefit).

To keep the permission grant small, Terraform manages **only the API Gateway**
(additive), referencing the existing Lambda via a data source — instead of the whole
stack, which would have needed `iam:CreateRole` / `lambda:CreateFunction`. Eric
attached one inline policy (`analyst-apigateway`: apigateway:* + a few lambda perms)
and the apply created 5 resources. `curl` returned our handler's 401 → endpoint good.
Deleted the dead Function URL. Eric pasted the API Gateway URL into Discord's
Interactions Endpoint → verified → `/analysis` returns the stub. **Live.**

### Decisions & conclusions
- **Function URLs are unusable in this account** → always use API Gateway for public
  Lambda endpoints. (Saved to memory: `project-lambda-url-block`.)
- **Native deps (PyNaCl) must be packaged with the Linux wheel** for Lambda.
- **Split provisioning vs code-deploy:** console/Terraform for infra (needs privilege),
  `update-function-code` for code (narrow perms, per-merge via GHA).
- **Terraform owns the gateway only, for now** — folding the Lambda/role into
  Terraform later would need broader IAM and is deferred.
- **Diagnostic:** direct `aws lambda invoke` isolates code correctness from
  endpoint/auth problems — reach for it first next time an endpoint 403s.

---

## What's running in production (monitors — all merged and deployed)

| Source | Approach |
|---|---|
| Becker's Payer | RSS |
| KFF Health News | RSS |
| Cigna Newsroom | RSS |
| Sutter Health | RSS |
| UC Davis Health | RSS |
| UCSD Health | HTML scraping |
| UCI Health | HTML scraping |
| UCLA Health | HTML scraping |
| UCSF | HTML scraping |
| Sharp Health | HTML scraping |
| Scripps Health | HTML scraping |
| Providence CA | HTML scraping |
| Hoag Health | Sitemap (AGE-92) |
| John Muir Health | HTML scraping (AGE-91) |

---

## Lambda schedule — 1am run removal (Eric's action, still pending)

Eric is deleting the 1am EventBridge rule manually in AWS Console. IAM user
`github-actions-deploy` lacks `events:*` permissions.
- EventBridge → Rules → us-west-1 → find the 1am cron rule → Delete
- 1am PT = cron(0 8 * * ? *) or cron(0 9 * * ? *) depending on DST
- Leave 7am, 1pm, and 4th run untouched

---

## Key facts

- **AnalystAgent Lambda:** `analyst-handler`, us-west-1, handler
  `agent.analyst.interactions.handler`, python3.12/x86_64
- **Monitor Lambda:** `health-insurance-monitor`, us-west-1
- **Databases:** Neon (prod, `DATABASE_URL`), Docker Postgres (local,
  `DATABASE_URL_LOCAL`) — smoke tests always use `DATABASE_URL_LOCAL`
- **IAM:** `github-actions-deploy` — Lambda + CloudWatch read, `update-function-code`,
  plus inline `analyst-apigateway` (apigateway:* + a few lambda perms); lacks
  EventBridge and IAM-create perms
- **`.env`** now holds `DISCORD_APPLICATION_ID`, `DISCORD_PUBLIC_KEY`,
  `DISCORD_BOT_TOKEN`, `DISCORD_GUILD_ID` for the AnalystAgent Discord app

---

_Last updated: 2026-08-25 — AnalystAgent walking skeleton shipped and live._
