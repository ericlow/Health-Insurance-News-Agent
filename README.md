# Health Insurance News Agent

A multi-agent system that monitors health insurance industry news for significant relationship changes between major carriers and providers — acquisitions, mergers, partnerships, divestitures, and contract terminations.

## How it works

The pipeline runs on a schedule (default: hourly). Each run:

1. **Scraper** — fetches new articles from Becker's Payer and KFF Health News RSS feeds
2. **Triage** — calls Claude Haiku to flag articles that describe a meaningful carrier/provider relationship change
3. **Summarizer** — calls Claude Sonnet to produce a structured 4-field brief for each flagged article
4. **Discord notifier** — posts each brief to a Discord webhook

*We are looking for major changes in relationships — acquisitions, mergers, partnerships, divestitures, or terminations of deals between major insurance carriers and providers.*

---

## Setup

### Prerequisites

- Python 3.9+
- PostgreSQL (local or Docker; default config expects `localhost:5432`)
- An [Anthropic API key](https://console.anthropic.com/)
- A Discord webhook URL (Server Settings → Integrations → Webhooks)

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd Health-Insurance-News-Agent
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure RSS feeds

```bash
cp config.example.json config.json
```

The default `config.json` monitors Becker's Payer RSS feed. Edit the `rss_feeds` array to add or change sources.

### 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in your values:

```
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/health_insurance_news
ANTHROPIC_API_KEY=sk-ant-...
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
MONITOR_INTERVAL_HOURS=8
```

### 5. Initialize the database

Creates the `health_insurance_news` database and applies the schema. Run once:

```bash
python db/init_db.py
```

### 6. Run the pipeline manually

```bash
python -m scheduler
```

This runs one full scrape → triage → summarize → notify cycle and exits. Expect it to take 15–30 seconds. Briefings for any flagged articles will appear in your Discord channel.

---

## Running on a schedule (cron)

To run the pipeline hourly in the background, add this cron entry:

```
0 * * * * cd /path/to/Health-Insurance-News-Agent && .venv/bin/python -m scheduler >> /var/log/health-insurance-monitor.log 2>&1
```

The `MONITOR_INTERVAL_HOURS` env var is available for future scheduler-driven loops but the primary production pattern is cron.

---

## Running tests

```bash
pytest
```

---

## Documentation

- [`docs/inputs.md`](docs/inputs.md) — dated log of domain expert inputs; the source of truth for what this system should look for and why
- [`CLAUDE.md`](CLAUDE.md) — guidance for working in this repo with Claude Code
