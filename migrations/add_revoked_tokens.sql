-- Persist JWT revocations so logged-out access tokens cannot be reused.
-- Apply this migration before deploying the application code.

BEGIN;

CREATE TABLE IF NOT EXISTS revoked_tokens (
    id BIGSERIAL PRIMARY KEY,
    jti VARCHAR(36) NOT NULL UNIQUE,
    token_type VARCHAR(16) NOT NULL,
    user_identity VARCHAR(255) NOT NULL,
    revoked_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMPTZ NULL
);

CREATE INDEX IF NOT EXISTS ix_revoked_tokens_jti
    ON revoked_tokens (jti);

CREATE INDEX IF NOT EXISTS ix_revoked_tokens_expires_at
    ON revoked_tokens (expires_at);

COMMIT;
