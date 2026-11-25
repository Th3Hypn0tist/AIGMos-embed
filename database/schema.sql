-- AirQualityMonitorSystem / AirQualityMon
-- PostgreSQL + TimescaleDB. Execute against an EMPTY, dedicated database.
-- No automatic data retention, compression or aggregates at this stage.
--
-- Example:
--   sudo -u postgres psql -d "AirQualityMon" -v ON_ERROR_STOP=1 -f database/schema.sql
--
-- PRECONDITION: PostgreSQL has preloaded timescaledb and been restarted.
-- Time-series samples have NO standalone primary key; a TimescaleDB
-- hypertable's UNIQUE/PRIMARY KEY must contain the partitioning timestamp.

CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE SCHEMA IF NOT EXISTS aqm;

CREATE TABLE IF NOT EXISTS aqm.samples (
    received_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    device_id             TEXT NOT NULL,
    boot_id               CHAR(16) NOT NULL,
    seq                   BIGINT NOT NULL CHECK (seq >= 0),
    uptime_ms             BIGINT NOT NULL CHECK (uptime_ms >= 0),
    temperature_c         REAL,
    bmp_temperature_c     REAL,
    humidity_rh           REAL CHECK (humidity_rh IS NULL OR humidity_rh BETWEEN 0 AND 100),
    pressure_hpa          REAL CHECK (pressure_hpa IS NULL OR pressure_hpa BETWEEN 300 AND 1200),
    eco2_ppm              INTEGER CHECK (eco2_ppm IS NULL OR eco2_ppm BETWEEN 0 AND 65535),
    tvoc_ppb              INTEGER CHECK (tvoc_ppb IS NULL OR tvoc_ppb BETWEEN 0 AND 65535),
    ccs_warming_up        BOOLEAN NOT NULL DEFAULT FALSE,
    ccs_error             SMALLINT NOT NULL DEFAULT 0 CHECK (ccs_error BETWEEN 0 AND 255),
    humidity_chip         TEXT NOT NULL DEFAULT 'unknown',
    humidity_diag         TEXT NOT NULL DEFAULT '',
    rssi_dbm              SMALLINT
);

-- This legacy-compatible create_hypertable call works with older packaged
-- TimescaleDB versions, including the Debian 13 (2.19.x) family.
SELECT create_hypertable(
    'aqm.samples',
    'received_at',
    if_not_exists => TRUE,
    chunk_time_interval => INTERVAL '7 days'
);

CREATE INDEX IF NOT EXISTS samples_device_time_idx
    ON aqm.samples (device_id, received_at DESC);

-- The time-partitioned samples hypertable cannot enforce uniqueness on
-- (device_id, boot_id, seq) alone. Keep lightweight, transactional dedupe
-- keys in a regular PostgreSQL table so HTTP retries cannot double-insert.
CREATE TABLE IF NOT EXISTS aqm.ingest_keys (
    device_id             TEXT NOT NULL,
    boot_id               CHAR(16) NOT NULL,
    seq                   BIGINT NOT NULL CHECK (seq >= 0),
    received_at           TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (device_id, boot_id, seq)
);

-- Run as database owner AFTER creating the restricted ingest login:
-- GRANT CONNECT ON DATABASE "AirQualityMon" TO aqm_ingest;
-- GRANT USAGE ON SCHEMA aqm TO aqm_ingest;
-- GRANT INSERT ON aqm.samples TO aqm_ingest;
-- GRANT INSERT, SELECT ON aqm.ingest_keys TO aqm_ingest;
