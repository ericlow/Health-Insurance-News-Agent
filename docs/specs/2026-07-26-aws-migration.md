# Spec: AWS Migration — Lambda + Neon

**Linear issue:** AGE-69
**Status:** Draft
**Decisions captured in:** `docs/adr/ADR-001-database-host.md`, `docs/adr/ADR-002-compute-platform.md`

---

## Goal

Move the pipeline off the local laptop and onto cloud infrastructure so it runs reliably without Docker Desktop or a connected Mac. The laptop remains the only place backfill runs (backfill requires headed Chrome; Lambda cannot run it).

---

## Target architecture

| Concern | Current | After migration |
|---|---|---|
| Scheduling | macOS LaunchAgent (4x/day) | EventBridge Scheduler (cron, same 4x/day cadence) |
| Compute | Python process on laptop | AWS Lambda |
| Database | Local Docker Postgres | Neon (serverless Postgres 16) |
| Secrets | `.env` file | Lambda environment variables |
| Logging | `/tmp/health-insurance-monitor.log` | CloudWatch Logs |
| Deployment | Manual (`git pull`) | GitHub Actions (push-to-main triggers deploy) |
| Backfill | Playwright + headed Chrome on laptop | **Unchanged — laptop only** |

---

## Constraints

- Free tier only. Cost ceiling: **$10/month** — stop and reassess if any service exceeds this.
- No code changes to core pipeline logic. The Lambda handler is a thin wrapper around the existing `run_pipeline()` function.
- `psycopg2` requires a Linux-compiled binary on Lambda. Use `psycopg2-binary` packaged in a Lambda layer.
- Neon compute auto-suspends after 5 minutes of inactivity. `psycopg2.connect()` blocks during wake (~500ms–1s). Do **not** set a short `connect_timeout` in the connection string.

---

## Implementation steps

### Step 1 — Neon database

1. Create a Neon project at [neon.tech](https://neon.tech) (free tier, Postgres 16).
2. Note the connection string (format: `postgres://user:password@host/dbname?sslmode=require`).
3. Run migrations against Neon:
   ```bash
   pg_dump -h localhost -U postgres health_insurance_monitor > /tmp/hian_backup.sql
   psql <neon-connection-string> < /tmp/hian_backup.sql
   ```
4. Verify row counts match local DB before proceeding.
5. Update local `.env` with `DATABASE_URL=<neon-connection-string>` and run the pipeline once locally to confirm psycopg2 connects and a full run completes against Neon.

### Step 2 — Lambda handler

Add `agent/lambda_handler.py`:

```python
from scheduler import run_pipeline
import logging

log = logging.getLogger()
log.setLevel(logging.INFO)

def handler(event, context):
    run_pipeline()
```

No changes to `scheduler.py`. `run_pipeline()` already has the `psycopg2.OperationalError` guard that posts to Discord on DB failure.

### Step 3 — Lambda layer (psycopg2-binary)

Lambda runs on Amazon Linux 2023 (ARM64 or x86_64). Wheels must match. Two options:

**Option A (recommended): use a pre-built public layer**
- `jkehler/awslambda-psycopg2` provides a compiled psycopg2 for Lambda. Pin the version matching the psycopg2-binary version in `requirements.txt`.

**Option B: build locally**
```bash
pip install psycopg2-binary \
    --platform manylinux2014_x86_64 \
    --target ./layer/python \
    --only-binary=:all:
zip -r psycopg2_layer.zip layer/
aws lambda publish-layer-version \
    --layer-name psycopg2 \
    --zip-file fileb://psycopg2_layer.zip \
    --compatible-runtimes python3.12
```

### Step 4 — Lambda function

1. Create the Lambda function:
   - Runtime: Python 3.12
   - Architecture: x86_64
   - Handler: `agent.lambda_handler.handler`
   - Timeout: 5 minutes (pipeline currently runs in ~20–30s; 5 min is headroom without hitting the 15-min max)
   - Memory: 256 MB
2. Package and upload the deployment zip (see Step 6 for GitHub Actions automation).
3. Set environment variables on the Lambda function (replaces `.env`):
   - `DATABASE_URL`
   - `ANTHROPIC_API_KEY`
   - `DISCORD_WEBHOOK_URL`
   - `DISCORD_UNCERTAIN_WEBHOOK_URL`
   - `DISCORD_NO_WEBHOOK_URL`
   - `DISCORD_HEALTH_CHECK_WEBHOOK_URL`
   - Any source-specific feed URLs if set via env

### Step 5 — EventBridge Scheduler

Create a schedule that matches the current LaunchAgent cadence (midnight, 6am, noon, 6pm PT):

```
cron(0 8,14,20,2 * * ? *)   # UTC: midnight/6am/noon/6pm PT (PST = UTC-8)
```

Note: EventBridge cron runs in UTC. Adjust for daylight saving time if precision matters (PT = UTC-7 in summer, UTC-8 in winter). For this pipeline, ±1 hour is acceptable — use a fixed UTC offset.

Target: the Lambda function ARN. Add the `lambda:InvokeFunction` permission to the EventBridge Scheduler role.

### Step 6 — GitHub Actions deployment

`.github/workflows/deploy.yml`:

```yaml
name: Deploy to Lambda

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt --target ./package
          # psycopg2-binary is in the Lambda layer; exclude it from the zip
          rm -rf ./package/psycopg2* ./package/psycopg2_binary*

      - name: Package
        run: |
          cp -r agent db config.py scheduler.py ./package/
          cd package && zip -r ../deployment.zip .

      - name: Deploy
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          AWS_DEFAULT_REGION: us-east-1
        run: |
          aws lambda update-function-code \
            --function-name health-insurance-monitor \
            --zip-file fileb://deployment.zip
```

Add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` as GitHub Actions secrets. Use an IAM user with `lambda:UpdateFunctionCode` only — no broader permissions.

### Step 7 — Cut over

1. Verify one manual Lambda invocation completes successfully (check CloudWatch logs + Discord health check channel).
2. Verify EventBridge fires on schedule for at least one run.
3. Unload the LaunchAgent:
   ```bash
   launchctl unload ~/Library/LaunchAgents/com.ericlow.health-insurance-monitor.plist
   ```
4. Delete the LaunchAgent plist.

---

## Rollback

If Lambda is broken and a run is overdue:
```bash
python3 -m scheduler   # run pipeline locally against Neon
```
The `DATABASE_URL` in `.env` should always point to Neon after Step 1 — local runs and Lambda runs hit the same DB.

---

## Out of scope

- **Backfill**: laptop only; Playwright + headed Chrome cannot run in Lambda.
- **API Gateway**: deferred until A1/A2 conversational agents are built (AGE-67, AGE-68).
- **Secrets Manager**: Lambda env vars are sufficient at this scale.
- **VPC**: not needed; Neon accepts public connections with SSL.
- **Multiple environments (staging/prod)**: single Lambda function; Neon DB branching available if needed for migration testing.

---

## Success criteria

- [ ] Pipeline runs end-to-end on Lambda (scrape → triage → brief → Discord alert)
- [ ] CloudWatch logs show a completed run
- [ ] Discord health check channel receives a post from Lambda
- [ ] LaunchAgent is unloaded and deleted
- [ ] `git push` to main triggers automatic Lambda deploy via GitHub Actions
- [ ] Cost stays at $0 (well within free tier)
