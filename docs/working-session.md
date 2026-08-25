# Working Session — 2026-08-25

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
