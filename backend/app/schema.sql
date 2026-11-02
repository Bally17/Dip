CREATE EXTENSION IF NOT EXISTS timescaledb;

CREATE TABLE IF NOT EXISTS participants (
    code text PRIMARY KEY,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS sessions (
    id text PRIMARY KEY,
    participant text NOT NULL REFERENCES participants (code),
    started_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS samples (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id),
    phase int NOT NULL,
    heart_rate real,
    head jsonb NOT NULL,
    left_hand jsonb,
    right_hand jsonb
);
SELECT create_hypertable('samples', 'ts', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS events (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id),
    phase int NOT NULL,
    kind text NOT NULL,
    value_ms real NOT NULL
);

CREATE TABLE IF NOT EXISTS questionnaires (
    ts timestamptz NOT NULL,
    session text NOT NULL REFERENCES sessions (id),
    phase int NOT NULL,
    score real NOT NULL
);
