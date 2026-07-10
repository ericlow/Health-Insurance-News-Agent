CREATE TABLE IF NOT EXISTS scrape_runs (
    id              SERIAL PRIMARY KEY,
    source          TEXT NOT NULL,
    started_at      TIMESTAMPTZ NOT NULL,
    completed_at    TIMESTAMPTZ,
    status          TEXT NOT NULL CHECK (status IN ('running', 'completed', 'failed')),
    articles_found  INTEGER,
    articles_new    INTEGER,
    error_message   TEXT
);

CREATE TABLE IF NOT EXISTS articles (
    id              SERIAL PRIMARY KEY,
    url             TEXT UNIQUE NOT NULL,
    title           TEXT,
    published_at    TIMESTAMPTZ,
    body_text       TEXT,
    source          TEXT NOT NULL,
    category        TEXT,                        -- first URL path segment (e.g. 'contracting', 'payer', 'financial')
    tags            TEXT[],                      -- all WordPress taxonomy terms from RSS feed (e.g. ['Payer', 'Medicare Advantage'])
    first_seen_at   TIMESTAMPTZ NOT NULL,
    scrape_run_id   INTEGER REFERENCES scrape_runs(id)
);

CREATE TABLE IF NOT EXISTS triage_results (
    id              SERIAL PRIMARY KEY,
    article_id      INTEGER NOT NULL REFERENCES articles(id),
    scrape_run_id   INTEGER REFERENCES scrape_runs(id),
    flag            TEXT NOT NULL CHECK (flag IN ('yes', 'uncertain', 'no')),
    summary         TEXT,
    confidence      INTEGER,
    scope           TEXT,
    reason          TEXT,
    model           TEXT NOT NULL,
    triaged_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS briefings (
    id                  SERIAL PRIMARY KEY,
    article_id          INTEGER NOT NULL REFERENCES articles(id),
    triage_result_id    INTEGER NOT NULL REFERENCES triage_results(id),
    scrape_run_id       INTEGER REFERENCES scrape_runs(id),
    what_happened       TEXT NOT NULL,
    who                 TEXT NOT NULL,
    impact              TEXT NOT NULL,
    why_it_matters      TEXT NOT NULL,
    model               TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    discord_sent_at     TIMESTAMPTZ
);
