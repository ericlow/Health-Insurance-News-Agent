# ADR-001: Database Host

**Date:** 2026-07-18
**Status:** Accepted

---

## Context

The pipeline currently runs against a local PostgreSQL instance in Docker Desktop. Moving to the cloud requires an externally hosted Postgres database. The constraint is free or very low cost, with no hard expiration on the free tier.

---

## Decision

**Neon.**

Neon and Supabase are close — both offer permanently free serverless Postgres that works with our existing psycopg2 stack without code changes. The tiebreaker was reliability under edge cases: Supabase pauses the entire project after 1 week of inactivity, which would break the pipeline and require a manual dashboard intervention to recover. Neon only suspends the compute process (not the project), wakes automatically on the next connection in ~500ms–1s, and never requires manual intervention. For an automated pipeline, that difference matters even if it rarely triggers.

RDS and EC2-hosted Postgres were eliminated early — RDS has a 12-month free tier expiration and EC2 couples the database to the compute host.

---

## Options Considered

### 1. AWS RDS (db.t3.micro)
- 750 hours/month free — but only for 12 months, then ~$15–20/month
- Eliminated: time-limited free tier is a cost time bomb

### 2. PostgreSQL on EC2
- Free if running on a free-tier EC2 instance
- Couples the database to the compute host — if compute changes, database moves too
- Eliminated: tight coupling, no managed backups

### 3. Supabase
- Free tier: always-on compute, 500MB storage
- Neon and Supabase are functionally equivalent for this project — same Postgres, same driver, same connection string format
- Projects pause after 1 week of complete inactivity; connections are refused until manually unpaused via dashboard
- Includes auth, REST API, realtime — features irrelevant to this project
- Not chosen: project-level pause risk is the deciding factor; if Neon's free tier changes, Supabase is a near-identical migration

### 4. Neon ✓
- Free tier: serverless Postgres 16, 0.5GB storage, 190 compute hours/month, permanently free
- Compute auto-suspends after 5 minutes of inactivity; wakes in ~500ms–1s on new connection
- psycopg2 `connect()` blocks during wake — no failure, no code changes required
- No project-level pausing — only the compute process suspends, data always accessible
- DB branching available (useful for testing migrations against a copy of prod)

### 5. CockroachDB / PlanetScale
- CockroachDB: 10GB free but distributed SQL with Postgres compatibility gaps that could break existing queries
- PlanetScale: MySQL only
- Neither seriously evaluated

---

## Consequences

- All environments (prod, dev) use Neon; local Docker Postgres is no longer required after migration
- Every pipeline run incurs a ~1s cold start on the DB connection — acceptable at 8-hour intervals
- Do not set a short `connect_timeout` in the connection string, as this could race with Neon's wake time
- Data migration: `pg_dump` local DB + `psql` restore to Neon
- Storage limit is 0.5GB — monitor table growth; articles table is the primary consumer
- Vendor risk: Neon is a startup; if free tier terms change, Supabase is a like-for-like fallback
