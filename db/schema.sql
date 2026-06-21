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
