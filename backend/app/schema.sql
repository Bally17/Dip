CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS users (
    username text PRIMARY KEY,
    password_hash text NOT NULL,
    role text NOT NULL CHECK (role IN ('admin', 'researcher'))
);

CREATE TABLE IF NOT EXISTS participants (
    code text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id text PRIMARY KEY,
    participant text NOT NULL REFERENCES participants (code) ON DELETE CASCADE,
    started_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS samples (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    phase int NOT NULL,
    heart_rate real,
    head jsonb NOT NULL,
    left_hand jsonb,
    right_hand jsonb
);

SELECT create_hypertable('samples', 'ts', if_not_exists => TRUE);

CREATE INDEX IF NOT EXISTS samples_session_ts ON samples (session, ts DESC);

CREATE TABLE IF NOT EXISTS events (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    phase int NOT NULL,
    kind text NOT NULL,
    value_ms real NOT NULL
);

CREATE TABLE IF NOT EXISTS questionnaires (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id) ON DELETE CASCADE,
    phase int NOT NULL,
    score real NOT NULL
);

SELECT add_retention_policy('samples', INTERVAL '365 days', if_not_exists => TRUE);

CREATE MATERIALIZED VIEW IF NOT EXISTS samples_1s
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT time_bucket('1 second', ts) AS bucket,
       session,
       avg(heart_rate) AS hr_avg,
       count(*) AS n
FROM samples
GROUP BY bucket, session
WITH NO DATA;

SELECT add_continuous_aggregate_policy('samples_1s',
    start_offset => INTERVAL '1 hour',
    end_offset => INTERVAL '1 second',
    schedule_interval => INTERVAL '1 minute',
    if_not_exists => TRUE);
