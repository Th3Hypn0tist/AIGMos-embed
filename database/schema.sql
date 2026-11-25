-- Run this as the database/schema owner in a dedicated database (air_quality).
-- PostgreSQL, plain table: good for this initial single-device workload.
CREATE SCHEMA IF NOT EXISTS aqm;

CREATE TABLE IF NOT EXISTS aqm.samples (
    id                    BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
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
    ccs_error             SMALLINT NOT NULL DEFAULT 0,
    humidity_chip         TEXT NOT NULL DEFAULT 'unknown',
    humidity_diag         TEXT NOT NULL DEFAULT '',
    rssi_dbm              SMALLINT,
    CONSTRAINT samples_unique_sample UNIQUE (device_id, boot_id, seq)
);

-- Fast most-recent-values and time-range queries for a selected device.
CREATE INDEX IF NOT EXISTS samples_device_time_idx
    ON aqm.samples (device_id, received_at DESC);

-- After creating the restricted user, run the following as schema owner:
-- GRANT USAGE ON SCHEMA aqm TO aqm_ingest;
-- GRANT INSERT, SELECT (id) ON aqm.samples TO aqm_ingest;
-- GRANT USAGE ON SEQUENCE aqm.samples_id_seq TO aqm_ingest;