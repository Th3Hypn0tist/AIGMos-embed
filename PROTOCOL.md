# AQM Protocol

Status: agreed architecture; wire specification v1 draft, not yet implemented.

## Architecture

All nodes (ESP8266, ESP32-C6 and future platforms) use the same platform- and sensor-independent OSC over UDP protocol. Python backend receives, validates and writes to PostgreSQL (AirQualityMon). Database credentials and SCRAM stay on the server. No encryption or authentication on the node-to-backend link; restrict it to the trusted IOT network. Proposed UDP port: 9000. No external OSC libraries: Arduino C++ encoder and Python socket/struct decoder.

## Identity and sampling

- Persistent MAC-based node_id; new boot_id at each boot.
- Monotonic sequence within each boot; uptime in milliseconds.
- Protocol version independent of firmware version.
- Automatic node registration and capability discovery; no per-node backend configuration.
- Send one self-contained OSC bundle per measurement cycle (5 seconds). Include identity, platform, firmware, protocol version, boot ID, sequence, uptime and sensor capabilities so recovery does not depend on a previous UDP packet.
- Each measurement identifies its source sensor instance and standardized quantity, allowing multiple sensors measuring the same quantity.
- Missing or invalid readings are omitted, never replaced by zero. Backend maps missing legacy fields to SQL NULL.
- Backend timestamps receipt and deduplicates by node_id, boot_id, sequence. UDP loss is acceptable for periodic measurements.
- Manual calibration observations require acknowledgment; retry/idempotency details remain to be specified.

## Quantities

| Identifier | Unit |
|---|---|
| temperature | °C |
| humidity | %RH |
| pressure | hPa |
| eco2 | ppm (estimated CO2, not direct measurement) |
| tvoc | ppb |

Extensible quantity registry; sensor model is metadata, not a protocol discriminator. Preserve raw readings and separate calibration observations/offsets. Pressure sensor temperature is primary for current dashboard; humidity sensor temperature remains available separately.

## OSC message families (draft)

- /aqm/register : node identity and version metadata
- /aqm/sensors : sensor instances and capabilities
- /aqm/sample : sample identity and timing
- /aqm/temperature/raw, /aqm/temperature/pressure, /aqm/humidity, /aqm/pressure, /aqm/eco2, /aqm/tvoc : initial proposed measurement addresses; source sensor instance must be included
- /aqm/rssi : network diagnostics
- /aqm/calibration : manual reference observations

Exact type tags, argument order, generic extensible measurement address, acknowledgment format and version compatibility rules must be finalized before implementation. These are not yet a frozen wire contract.

## Firmware composition

One shared Arduino C++ sketch for ESP8266 and ESP32-C6. Compile-time platform abstraction; runtime detection and activation of sensor modules. Inactive drivers are compiled in but not initialized. Separate modules for BMP180, BMP280, DHT11, HDC1080, Si7021-compatible and CCS811. Separate platform, network, sensor registry, OSC and local web components. Preserve local Web UI, JSON API, DHCP/static IP selection and calibration functionality. No direct PostgreSQL client on nodes after migration.

BMP180: I2C 0x77, register 0xD0 = 0x55 (also BMP085 compatible).
BMP280: I2C 0x76/0x77, register 0xD0 = 0x58.
DHT11: valid GPIO response and checksum.
HDC1080 and Si7021-compatible: existing I2C 0x40 probes.
CCS811: I2C 0x5A/0x5B and hardware ID.

Node 02: Wemos D1 Mini ESP8266; SDA GPIO4 (D2), SCL GPIO5 (D1), DHT11 DATA GPIO14 (D5); BMP180 expected, hardware detection still to verify. Node 01: existing ESP32-C6 CJMCU-8128 (BMP280, humidity, CCS811). Retain verified platform-specific wiring settings.

## Backend and database

Proposed backend server/aqm_osc.py, local configuration server/config.json (credentials excluded from version control). Reuse existing aqm.ingest() initially for compatibility. Existing fixed-column schema must eventually support arbitrary quantities and multiple sensor instances without schema changes for each new sensor type. Design migration separately; preserve existing data and dashboard compatibility. PROTOCOL.md is the shared SSOT for firmware, backend and dashboard integration.

## Implementation status

Architecture only. Existing firmware, database and dashboard unchanged. Finalize wire contract, implement sensor modules and common firmware, implement Python receiver, verify both hardware targets, and migrate existing C6 node to OSC.
