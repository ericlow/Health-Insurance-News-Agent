# ADR-002: Compute Platform

**Date:** 2026-07-18
**Status:** Accepted

---

## Context

The pipeline currently runs as a Python daemon on a local laptop (APScheduler triggers every 8 hours). Moving to the cloud requires a hosted compute platform that can: (1) run the scheduled scraping and triage pipeline, and (2) serve conversational agent requests (A1/A2). The constraint is free or very low cost indefinitely. The codebase is Python and uses psycopg2 (a C-extension Postgres driver).

---

## Decision

**AWS Lambda**, with EventBridge Scheduler for cron triggering and API Gateway for HTTP endpoints.

AWS was chosen over Google Cloud Functions on familiarity and ecosystem grounds — both are technically equivalent for this use case and the decision is a close call. Lambda's free tier (1M invocations/month, 400K GB-seconds) comfortably covers our volume (~90 pipeline runs/month). EventBridge Scheduler handles the 8-hour cron; API Gateway gives Lambda a public URL for conversational agent requests.

The conversational agent use case works cleanly with Lambda: the Claude API is stateless by design, so each user message is one Lambda invocation — the handler reads conversation history from Neon, calls Claude with full context, saves the new turn, and returns the response. No persistent process needed.

Secrets are stored as Lambda environment variables. Deployment is via GitHub Actions. Logging goes to CloudWatch (built-in, no setup required).

---

## Options Considered

### 1. EC2 (t2.micro)
- Simplest migration — existing code runs unchanged, no refactoring
- Free tier: 750 hours/month for 12 months only, then ~$8/month
- Requires server management: SSH, patching, process monitoring
- Not chosen: 12-month expiration; ongoing management overhead

### 2. Fly.io
- Runs small containers close to users; simple deploy (`fly deploy`)
- Free allowance: 3 shared-CPU VMs, 256MB RAM
- Good for persistent long-running processes
- Not chosen: adds containerization overhead; persistent process not required for our use case

### 3. Cloudflare Workers
- Extremely fast edge execution, 3M req/month free
- Built for JS/TS edge use cases: HTTP rewrites, A/B testing, auth middleware, API proxies — not background data pipelines
- Python support is beta; C-extension packages (including psycopg2) will not run
- Not chosen: wrong tool category; Python library limitations

### 4. Vercel Functions
- Simple git-push deployment, good for web apps
- Free (Hobby) plan cron minimum interval is once per day — our pipeline needs every 8 hours
- 10-second function timeout on free tier
- Not chosen: cron interval too coarse; timeout too short

### 5. Render
- Simple deployment, Python supported, cron jobs available
- Free tier web services spin down after 15 minutes of inactivity — causes ~30s cold start
- Not chosen: 30s cold start on every pipeline run is unacceptable

### 6. Google Cloud Functions ✦
- 2M invocations/month free (more generous than Lambda's 1M)
- HTTP triggers built-in — no API Gateway equivalent needed
- Cloud Scheduler for cron (simpler than EventBridge)
- Python supported, psycopg2 works
- Technically the stronger free-tier option; eliminated on ecosystem preference (AWS)

### 7. AWS Lambda ✓
- 1M invocations/month + 400K GB-seconds free, permanently
- EventBridge Scheduler for 8-hour cron trigger
- API Gateway for public HTTP endpoint (conversational agents)
- CloudWatch Logs built-in
- Python supported, psycopg2 works
- GitHub Actions for deployment

---

## Consequences

- Pipeline refactored from APScheduler daemon to a Lambda handler function
- No persistent in-memory state between invocations — all conversation history and pipeline state in Neon
- 15-minute hard timeout per invocation; pipeline currently runs in ~20s — well within limit; if pipeline ever grows to exceed this, it must be split into chained Lambda functions
- Secrets stored as Lambda environment variables (Secrets Manager unnecessary at this scale)
- API Gateway adds a small per-request cost above 1M requests/month — not expected to be reached
- Local laptop no longer required for the pipeline to run after migration
