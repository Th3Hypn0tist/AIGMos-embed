#pragma once
bool initCCS() {
  for (uint8_t addr : {uint8_t(0x5A), uint8_t(0x5B)}) {
    uint8_t id, status;
    if (!i2cRead(addr, 0x20, &id, 1) || id != 0x81) continue;
    if (!i2cRead(addr, 0x00, &status, 1)) continue;
    if (!(status & 0x10)) { // APP_VALID
      Serial.println("CCS811 firmware application not valid");
      continue;
    }
    if (!(status & 0x80)) { // FW_MODE: transition from boot to app.
      if (!i2cCommand(addr, 0xF4)) continue; // APP_START: register only, zero data.
      delay(120);
    }
    if (!i2cRead(addr, 0x00, &status, 1) || !(status & 0x80)) continue;
    const uint8_t mode = 0x10; // DRIVE_MODE 1: measure every second.
    if (!i2cWrite(addr, 0x01, &mode, 1)) continue;
    ccsAddress = addr;
    ccsStartedAt = millis();
    Serial.printf("CCS811 detected at 0x%02X, running 1 s mode\n", addr);
    return true;
  }
  Serial.println("CCS811 not found (check WAK -> GND)");
  return false;
}

void readCCS() {
  if (!ccsReady) return;

  // Feed environmental compensation to CCS811 whenever humidity is valid.
  if (isfinite(ambientTemp) && isfinite(humidityRH)) {
    const uint16_t h = (uint16_t)roundf(constrain(humidityRH, 0.0f, 100.0f) * 512.0f);
    const uint16_t t = (uint16_t)roundf(constrain(ambientTemp + 25.0f, 0.0f, 127.0f) * 512.0f);
    const uint8_t env[4] = {
      uint8_t(h >> 8), uint8_t(h), uint8_t(t >> 8), uint8_t(t)
    };
    i2cWrite(ccsAddress, 0x05, env, sizeof(env));
  }

  uint8_t status;
  if (!i2cRead(ccsAddress, 0x00, &status, 1)) return;
  if (status & 0x01) { // ERROR
    i2cRead(ccsAddress, 0xE0, &ccsError, 1);
    Serial.printf("CCS811 error 0x%02X\n", ccsError);
    return;
  }
  ccsError = 0;
  if (!(status & 0x08)) return; // DATA_READY

  uint8_t result[8];
  if (!i2cRead(ccsAddress, 0x02, result, sizeof(result))) return;
  if (result[4] & 0x01) {
    ccsError = result[5];
    return;
  }
  eco2 = u16be(result);
  tvoc = u16be(result + 2);
  lastGasAt = millis();
}

