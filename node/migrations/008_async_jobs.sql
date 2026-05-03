-- Migration 004: async job store (spec §14.5 / §15.4)
-- Backing table for lint/decay job status polling.

CREATE TABLE IF NOT EXISTS jobs (
    id           TEXT PRIMARY KEY,
    job_type     TEXT NOT NULL CHECK(job_type IN ('lint','decay')),
    status       TEXT NOT NULL CHECK(status IN ('pending','running','done','failed')) DEFAULT 'pending',
    scope        TEXT,
    estimated_s  INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT NOT NULL,
    started_at   TEXT,
    completed_at TEXT,
    result_json  TEXT,
    error        TEXT
);

CREATE INDEX IF NOT EXISTS idx_jobs_type_status ON jobs(job_type, status);
