# Legacy direct PostgreSQL solution

Snapshot of the pre-OSC implementation. Original firmware and legacy display sketches preserved. The existing ESP32-C6 can continue direct PostgreSQL ingest while ESP8266 is developed against OSC. Active database/schema.sql and air-dash remain unchanged at their existing paths; archived copies are for reference. Existing PHP server endpoints remain available at their original paths.

Migration order: verify ESP8266 Push to node end-to-end first, then migrate ESP32-C6. Do not flash existing devices automatically.
