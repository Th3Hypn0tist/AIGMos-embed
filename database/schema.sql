-- AirQualityMon / direct PostgreSQL ingestion, schema v1.
-- Run as postgres in the dedicated, empty AirQualityMon database.
\set ON_ERROR_STOP on
BEGIN;
CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE SCHEMA IF NOT EXISTS aqm;
REVOKE ALL ON SCHEMA aqm FROM PUBLIC;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'aqm_ingest') THEN
    CREATE ROLE aqm_ingest LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS aqm.nodes (
    node_id TEXT PRIMARY KEY CHECK (node_id ~ '^[0-9a-f]{12}$'),
    platform TEXT NOT NULL,
    firmware_version TEXT NOT NULL,
    name TEXT,
    location TEXT,
    first_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_seen TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS aqm.samples (
    received_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    node_id TEXT NOT NULL REFERENCES aqm.nodes(node_id),
    boot_id TEXT NOT NULL CHECK (boot_id ~ '^[0-9a-f]{16}$'),
    seq BIGINT NOT NULL CHECK (seq >= 0),
    uptime_ms BIGINT NOT NULL CHECK (uptime_ms >= 0),
    temperature_c REAL,
    bmp_temperature_c REAL,
    humidity_rh REAL CHECK (humidity_rh BETWEEN 0 AND 100),
    pressure_hpa REAL CHECK (pressure_hpa BETWEEN 300 AND 1200),
    eco2_ppm INTEGER CHECK (eco2_ppm BETWEEN 0 AND 65535),
    tvoc_ppb INTEGER CHECK (tvoc_ppb BETWEEN 0 AND 65535),
    ccs_warming_up BOOLEAN NOT NULL,
    ccs_error SMALLINT NOT NULL CHECK (ccs_error BETWEEN 0 AND 255),
    humidity_chip TEXT NOT NULL,
    humidity_diag TEXT NOT NULL,
    rssi_dbm SMALLINT
);

SELECT create_hypertable('aqm.samples', 'received_at',
    if_not_exists => TRUE, chunk_time_interval => INTERVAL '7 days');
CREATE INDEX IF NOT EXISTS samples_node_time_idx ON aqm.samples (node_id, received_at DESC);

-- Separate ordinary table: unique keys independent of hypertable time partition.
CREATE TABLE IF NOT EXISTS aqm.ingest_keys (
    node_id TEXT NOT NULL REFERENCES aqm.nodes(node_id),
    boot_id TEXT NOT NULL,
    seq BIGINT NOT NULL,
    PRIMARY KEY (node_id, boot_id, seq)
);

-- Single atomic database operation; no direct table permissions for devices.
CREATE OR REPLACE FUNCTION aqm.ingest(
    p_node TEXT, p_platform TEXT, p_version TEXT, p_boot TEXT,
    p_seq BIGINT, p_uptime BIGINT,
    p_temp REAL, p_bmp REAL, p_rh REAL, p_pressure REAL,
    p_eco2 INTEGER, p_tvoc INTEGER, p_warmup BOOLEAN, p_error SMALLINT,
    p_chip TEXT, p_diag TEXT, p_rssi SMALLINT
) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
AS $$
BEGIN
    INSERT INTO aqm.nodes(node_id, platform, firmware_version)
    VALUES (p_node, p_platform, p_version)
    ON CONFLICT (node_id) DO UPDATE SET
      platform = EXCLUDED.platform,
      firmware_version = EXCLUDED.firmware_version,
      last_seen = CURRENT_TIMESTAMP;
    INSERT INTO aqm.ingest_keys(node_id, boot_id, seq)
    VALUES (p_node, p_boot, p_seq) ON CONFLICT DO NOTHING;
    IF NOT FOUND THEN RETURN FALSE; END IF;
    INSERT INTO aqm.samples(node_id, boot_id, seq, uptime_ms,
      temperature_c, bmp_temperature_c, humidity_rh, pressure_hpa,
      eco2_ppm, tvoc_ppb, ccs_warming_up, ccs_error, humidity_chip, humidity_diag, rssi_dbm)
    VALUES (p_node, p_boot, p_seq, p_uptime, p_temp, p_bmp, p_rh, p_pressure,
      p_eco2, p_tvoc, p_warmup, p_error, p_chip, p_diag, p_rssi);
    RETURN TRUE;
END
$$;

-- Manual reference observations, independent of the continuous raw samples.
-- IR instruments measure surfaces; target identifies what was measured.
CREATE TABLE IF NOT EXISTS aqm.calibration_observations (
    observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    observed_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    node_id TEXT NOT NULL REFERENCES aqm.nodes(node_id),
    boot_id TEXT NOT NULL CHECK (boot_id ~ '^[0-9a-f]{16} IN SCHEMA aqm FROM PUBLIC, aqm_ingest;
REVOKE ALL ON FUNCTION aqm.ingest(TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,REAL,REAL,REAL,REAL,INTEGER,INTEGER,BOOLEAN,SMALLINT,TEXT,TEXT,SMALLINT) FROM PUBLIC;
GRANT CONNECT ON DATABASE "AirQualityMon" TO aqm_ingest;
GRANT USAGE ON SCHEMA aqm TO aqm_ingest;
GRANT EXECUTE ON FUNCTION aqm.ingest(TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,REAL,REAL,REAL,REAL,INTEGER,INTEGER,BOOLEAN,SMALLINT,TEXT,TEXT,SMALLINT) TO aqm_ingest;
COMMIT;
-- Set a random ASCII password interactively using psql: \password aqm_ingest
-- No retention policy. No table read/write grants for nodes.
),
    uptime_ms BIGINT NOT NULL CHECK (uptime_ms >= 0),
    raw_temperature_c REAL,
    raw_bmp_temperature_c REAL,
    raw_humidity_rh REAL CHECK (raw_humidity_rh BETWEEN 0 AND 100),
    thermal_camera_c REAL CHECK (thermal_camera_c BETWEEN -100 AND 300),
    laser_meter_c REAL CHECK (laser_meter_c BETWEEN -100 AND 300),
    ambient_reference_c REAL CHECK (ambient_reference_c BETWEEN -100 AND 150),
    target TEXT NOT NULL CHECK (target IN ('reference_surface','humidity_sensor','bmp280','ccs811','pcb','other')),
    note TEXT NOT NULL DEFAULT '' CHECK (length(note) <= 240),
    CHECK (thermal_camera_c IS NOT NULL OR laser_meter_c IS NOT NULL OR ambient_reference_c IS NOT NULL)
);
CREATE INDEX IF NOT EXISTS calibration_node_time_idx
    ON aqm.calibration_observations(node_id, observed_at DESC);

CREATE OR REPLACE FUNCTION aqm.record_calibration(
    p_node TEXT, p_boot TEXT, p_uptime BIGINT,
    p_temp REAL, p_bmp REAL, p_rh REAL,
    p_camera REAL, p_laser REAL, p_reference REAL, p_target TEXT, p_note TEXT
) RETURNS BOOLEAN
LANGUAGE plpgsql SECURITY DEFINER SET search_path = pg_catalog, pg_temp
AS $
BEGIN
    INSERT INTO aqm.calibration_observations(
      node_id, boot_id, uptime_ms, raw_temperature_c, raw_bmp_temperature_c,
      raw_humidity_rh, thermal_camera_c, laser_meter_c, ambient_reference_c, target, note)
    VALUES (p_node, p_boot, p_uptime, p_temp, p_bmp, p_rh,
      p_camera, p_laser, p_reference, p_target, p_note);
    RETURN TRUE;
END
$;
REVOKE ALL ON FUNCTION aqm.record_calibration(TEXT,TEXT,BIGINT,REAL,REAL,REAL,REAL,REAL,REAL,TEXT,TEXT) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION aqm.record_calibration(TEXT,TEXT,BIGINT,REAL,REAL,REAL,REAL,REAL,REAL,TEXT,TEXT) TO aqm_ingest;

REVOKE ALL ON ALL TABLES IN SCHEMA aqm FROM PUBLIC, aqm_ingest;
REVOKE ALL ON FUNCTION aqm.ingest(TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,REAL,REAL,REAL,REAL,INTEGER,INTEGER,BOOLEAN,SMALLINT,TEXT,TEXT,SMALLINT) FROM PUBLIC;
GRANT CONNECT ON DATABASE "AirQualityMon" TO aqm_ingest;
GRANT USAGE ON SCHEMA aqm TO aqm_ingest;
GRANT EXECUTE ON FUNCTION aqm.ingest(TEXT,TEXT,TEXT,TEXT,BIGINT,BIGINT,REAL,REAL,REAL,REAL,INTEGER,INTEGER,BOOLEAN,SMALLINT,TEXT,TEXT,SMALLINT) TO aqm_ingest;
COMMIT;
-- Set a random ASCII password interactively using psql: \password aqm_ingest
-- No retention policy. No table read/write grants for nodes.
