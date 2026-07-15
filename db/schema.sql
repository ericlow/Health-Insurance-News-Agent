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
    id                  SERIAL PRIMARY KEY,
    article_id          INTEGER NOT NULL REFERENCES articles(id),
    scrape_run_id       INTEGER REFERENCES scrape_runs(id),

    -- Stage 1: title screen (always populated)
    title_flag          TEXT CHECK (title_flag IN ('yes', 'uncertain', 'no')),
    title_confidence    INTEGER,
    title_scope         TEXT,
    title_reason        TEXT,

    -- Stage 2: article eval (NULL when dropped at title stage)
    article_flag        TEXT CHECK (article_flag IN ('yes', 'uncertain', 'no')),
    article_confidence  INTEGER,
    article_summary     TEXT,
    article_scope       TEXT,
    article_reason      TEXT,

    model               TEXT NOT NULL,
    triaged_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    discord_no_sent_at  TIMESTAMPTZ
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
