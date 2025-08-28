-- Temporal Logic Engine Database Schema
-- Initial migration for PreciagroMVP temporal logic system

-- Enable UUID extension for PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create enums for status fields
CREATE TYPE schedule_status AS ENUM ('pending','scheduled','done','skipped','expired','cancelled');
CREATE TYPE job_status AS ENUM ('queued','sending','sent','failed','cancelled');

-- Schedule Items Table
CREATE TABLE schedule_item (
  id BIGSERIAL PRIMARY KEY,
  farm_id TEXT NOT NULL,
  title TEXT NOT NULL,
  rule_id TEXT NOT NULL,
  rule_hash TEXT NOT NULL,
  priority TEXT NOT NULL,
  window_start_ts TIMESTAMPTZ NOT NULL,
  window_end_ts TIMESTAMPTZ NOT NULL,
  source_event_id TEXT NOT NULL,
  status schedule_status NOT NULL DEFAULT 'scheduled',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for schedule_item
CREATE INDEX ON schedule_item (farm_id, window_start_ts);
CREATE INDEX ON schedule_item (status, window_start_ts);

-- Notification Jobs Table
CREATE TABLE notification_job (
  id BIGSERIAL PRIMARY KEY,
  schedule_id BIGINT NOT NULL REFERENCES schedule_item(id) ON DELETE CASCADE,
  channel TEXT NOT NULL,
  send_after_ts TIMESTAMPTZ NOT NULL,
  dedupe_key TEXT NOT NULL,
  payload JSONB NOT NULL,
  attempts INT NOT NULL DEFAULT 0,
  status job_status NOT NULL DEFAULT 'queued',
  last_error TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Indexes for notification_job
CREATE UNIQUE INDEX notification_job_dedupe_idx ON notification_job(dedupe_key);
CREATE INDEX notification_due_idx ON notification_job (status, send_after_ts);

-- Task Outcomes Table
CREATE TABLE task_outcome (
  id BIGSERIAL PRIMARY KEY,
  schedule_id BIGINT NOT NULL REFERENCES schedule_item(id) ON DELETE CASCADE,
  outcome TEXT NOT NULL CHECK (outcome IN ('done','skipped')),
  actor TEXT NOT NULL, -- 'farmer' | 'system' | 'support'
  note TEXT,
  evidence_url TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Notification Audit Table (immutable audit - append-only)
CREATE TABLE notification_audit (
  id BIGSERIAL PRIMARY KEY,
  job_id BIGINT NOT NULL REFERENCES notification_job(id) ON DELETE CASCADE,
  event TEXT NOT NULL, -- 'enqueue'|'send_attempt'|'send_success'|'send_fail'|'receipt'
  data JSONB,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Update timestamp function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for updated_at columns
CREATE TRIGGER update_schedule_item_updated_at 
    BEFORE UPDATE ON schedule_item 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_notification_job_updated_at 
    BEFORE UPDATE ON notification_job 
    FOR EACH ROW 
    EXECUTE FUNCTION update_updated_at_column();

COMMIT;
