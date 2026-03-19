CREATE TABLE IF NOT EXISTS conversation_logs (
    id          BIGSERIAL PRIMARY KEY,
    session_id  VARCHAR(255)  NOT NULL,
    customer_id VARCHAR(255)  NOT NULL,
    channel     VARCHAR(50)   NOT NULL,
    customer_message TEXT     NOT NULL,
    agent_response   TEXT     NOT NULL,
    confidence  FLOAT         DEFAULT 0,
    escalated   BOOLEAN       DEFAULT FALSE,
    created_at  TIMESTAMPTZ   NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_conv_session  ON conversation_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_customer ON conversation_logs(customer_id);
CREATE INDEX IF NOT EXISTS idx_conv_created  ON conversation_logs(created_at);

CREATE TABLE IF NOT EXISTS security_logs (
    id          BIGSERIAL PRIMARY KEY,
    event_type  VARCHAR(100) NOT NULL,
    detail      TEXT,
    ip          VARCHAR(50),
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS ingestion_logs (
    id           BIGSERIAL PRIMARY KEY,
    filename     VARCHAR(500) NOT NULL,
    chunks_stored INT         DEFAULT 0,
    status       VARCHAR(50)  DEFAULT 'pending',
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
