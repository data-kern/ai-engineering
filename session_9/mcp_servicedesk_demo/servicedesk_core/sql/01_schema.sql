-- The KernMart IT service desk database. Real PostgreSQL.
-- This is the "system of record": the agent never touches these tables directly,
-- it can only call the tools that the MCP server builds on top of them.

CREATE TABLE employees (
    employee_id  TEXT PRIMARY KEY,                 -- E-1001
    name         TEXT NOT NULL,
    email        TEXT NOT NULL,
    role         TEXT NOT NULL DEFAULT 'employee'  -- employee | staff
);

CREATE TABLE accounts (
    employee_id      TEXT PRIMARY KEY REFERENCES employees,
    status           TEXT NOT NULL,                -- active | locked
    failed_attempts  INT  NOT NULL DEFAULT 0,
    security_hold    BOOLEAN NOT NULL DEFAULT FALSE,   -- security team froze it: NEVER unlock automatically
    mfa_enrolled     BOOLEAN NOT NULL DEFAULT TRUE
);

-- Things we did to an account (unlock, reset link). Used for the "3 per day" rule.
CREATE TABLE account_actions (
    id           BIGSERIAL PRIMARY KEY,
    employee_id  TEXT NOT NULL REFERENCES employees,
    action       TEXT NOT NULL,
    at           TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE reset_tokens (
    token_hash   TEXT PRIMARY KEY,                 -- we store a hash, never the token itself
    employee_id  TEXT NOT NULL REFERENCES employees,
    expires_at   TIMESTAMPTZ NOT NULL
);

CREATE TABLE kb_articles (
    article_id  TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    tags        TEXT NOT NULL,
    body        TEXT NOT NULL,
    -- PostgreSQL full-text search over title + tags + body
    search      TSVECTOR GENERATED ALWAYS AS
                (to_tsvector('english', title || ' ' || tags || ' ' || body)) STORED
);
CREATE INDEX kb_articles_search ON kb_articles USING GIN (search);

CREATE TABLE software_catalog (
    software       TEXT PRIMARY KEY,
    self_service   BOOLEAN NOT NULL,               -- may the agent hand it out without a manager?
    seats_total    INT NOT NULL,
    approval_note  TEXT NOT NULL DEFAULT ''
);

CREATE TABLE software_licenses (
    employee_id  TEXT NOT NULL REFERENCES employees,
    software     TEXT NOT NULL REFERENCES software_catalog,
    assigned_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (employee_id, software)            -- asking twice cannot take two seats
);

CREATE SEQUENCE ticket_number START 1001;

CREATE TABLE tickets (
    ticket_id          TEXT PRIMARY KEY,           -- IT-1001
    employee_id        TEXT NOT NULL REFERENCES employees,
    category           TEXT NOT NULL,
    summary            TEXT NOT NULL,
    details            TEXT NOT NULL,
    status             TEXT NOT NULL DEFAULT 'open',   -- open | resolved_by_agent | escalated | resolved_by_human
    urgency            TEXT NOT NULL DEFAULT 'normal',
    escalation_reason  TEXT,
    resolution         TEXT,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ticket_replies (
    id         BIGSERIAL PRIMARY KEY,
    ticket_id  TEXT NOT NULL REFERENCES tickets,
    author     TEXT NOT NULL,
    body       TEXT NOT NULL,
    at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Written by the MCP server for EVERY tool call: who asked, which tool, what happened.
CREATE TABLE audit_log (
    id           BIGSERIAL PRIMARY KEY,
    at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    employee_id  TEXT,
    tool         TEXT NOT NULL,
    arguments    JSONB NOT NULL DEFAULT '{}',
    outcome      TEXT NOT NULL,                    -- ok | refused | error
    detail       TEXT NOT NULL DEFAULT '',
    duration_ms  INT NOT NULL DEFAULT 0
);
