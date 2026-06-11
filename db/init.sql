-- Schema bootstrap for the MarketSentiment database.
-- Mounted into the postgres container at /docker-entrypoint-initdb.d/ so it
-- runs automatically on first startup. The Flask app also runs the same
-- statements idempotently at boot (see init_db in website/appFlask.py).

CREATE TABLE IF NOT EXISTS sentiment_history (
    id SERIAL PRIMARY KEY,
    fear_greed INTEGER,
    vix NUMERIC,
    summary_text TEXT,
    timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sentiment_history_timestamp
    ON sentiment_history (timestamp DESC);

CREATE TABLE IF NOT EXISTS vix_alerts_subscriptions (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    vix_threshold NUMERIC NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_alert_sent_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);
