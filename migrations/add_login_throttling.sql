-- Login throttling state. Apply before deploying the application code.
BEGIN;

CREATE TABLE IF NOT EXISTS login_attempts (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    ip_address VARCHAR(64) NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until TIMESTAMPTZ NULL,
    CONSTRAINT uq_login_attempt_username_ip UNIQUE (username, ip_address)
);

CREATE INDEX IF NOT EXISTS ix_login_attempt_locked_until
    ON login_attempts (locked_until);

CREATE TABLE IF NOT EXISTS login_ip_attempts (
    id SERIAL PRIMARY KEY,
    ip_address VARCHAR(64) NOT NULL UNIQUE,
    attempts INTEGER NOT NULL DEFAULT 0,
    window_started_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    locked_until TIMESTAMPTZ NULL
);

COMMIT;
