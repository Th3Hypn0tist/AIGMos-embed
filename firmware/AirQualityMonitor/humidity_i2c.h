#pragma once
void initHumidityI2C() {
  humidityChip = HUM_NONE;
  if (!hasDevice(0x40)) {
    humidityDiagnostic = "no_I2C_device_at_0x40";
    Serial.println("Humidity: NO response at I2C 0x40. Check scan/wiring/module.");
    return;
  }
  uint8_t id[2] = {0, 0};
  bool hdcIdRead = i2cReadStop(0x40, 0xFE, id, 2);
  if (hdcIdRead) Serial.printf("Humidity 0x40 HDC ID probe: 0x%04X\n", u16be(id));
  else Serial.println("Humidity 0x40 HDC ID probe: read failed");

  // HDC1080 manufacturer ID = 0x5449 (TI). Crucially, the HDC1080's
  // default CONFIG is 0x1000 (combined temperature + humidity measurement).
  // Configure it explicitly and read FOUR bytes for both values at once.
  if (hdcIdRead && u16be(id) == 0x5449) {
    const uint8_t config[2] = {0x10, 0x00};  // MODE=1; 14-bit T and RH.
    if (!i2cWrite(0x40, 0x02, config, 2)) {
      humidityDiagnostic = "hdc_configuration_write_failed";
      Serial.println("Humidity: HDC1080 config write failed");
      return;
    }
    humidityChip = HUM_HDC1080;
    humidityDiagnostic = "waiting_for_first_hdc_sample";
    Serial.println("Humidity sensor: HDC1080 (combined T/RH 4-byte mode)");
    return;
  }

  // SI7021, SI7020, HTU21D and compatible devices use command 0xE7.
  uint8_t userRegister = 0;
  if (i2cReadStop(0x40, 0xE7, &userRegister, 1)) {
    humidityChip = HUM_SI7021;
    humidityDiagnostic = "waiting_for_first_si_sample";
    Serial.printf("Humidity sensor: Si7021/HTU21D-compatible (user reg 0x%02X)\n",
                  userRegister);
    return;
  }

  humidityDiagnostic = "i2c_0x40_present_but_unknown_chip";
  Serial.println("Humidity: 0x40 responds, but neither HDC1080 nor Si7021/HTU21D responds to ID probe");
}

// Some Si7021/HTU21D no-hold readings return a temporary NACK while converting.
bool readSiSample(uint8_t command, uint16_t& result) {
  if (!i2cCommand(0x40, command)) return false;
  delay(40);
  uint8_t raw[2];
  for (uint8_t n = 0; n < 3; ++n) {
    if (i2cReadDirect(0x40, raw, sizeof(raw))) {
      result = u16be(raw) & 0xFFFC;
      return true;
    }
    delay(12);
  }
  return false;
}

void readHumidityI2C() {
  if (humidityChip == HUM_NONE) return;
  bool ok = false;
  float t = NAN, rh = NAN;
  const char* error = "unknown_read_error";

  if (humidityChip == HUM_HDC1080) {
    if (!i2cCommand(0x40, 0x00)) {
      error = "hdc_measurement_command_failed";
    } else {
      delay(35);
      uint8_t sample[4];
      if (!i2cReadDirect(0x40, sample, sizeof(sample))) {
        error = "hdc_4byte_read_failed";
      } else {
        t = (float)u16be(sample) * (165.0f / 65536.0f) - 40.0f;
        rh = (float)u16be(sample + 2) * (100.0f / 65536.0f);
        ok = true;
      }
    }
  } else if (humidityChip == HUM_SI7021) {
    uint16_t tRaw, rhRaw;
    if (!readSiSample(0xF3, tRaw)) {
      error = "si_temperature_read_failed";
    } else if (!readSiSample(0xF5, rhRaw)) {
      error = "si_humidity_read_failed";
    } else {
      t = 175.72f * (float)tRaw / 65536.0f - 46.85f;
      rh = 125.0f * (float)rhRaw / 65536.0f - 6.0f;
      ok = true;
    }
  }

  if (ok && isfinite(t) && isfinite(rh) &&
      t >= -40.0f && t <= 125.0f && rh >= -6.0f && rh <= 106.0f) {
    ambientTemp = t;
    humidityRH = constrain(rh, 0.0f, 100.0f);
    lastClimateAt = millis();
    humidityDiagnostic = "ok";
    humidityFailures = 0;
  } else {
    ambientTemp = NAN;
    humidityRH = NAN;
    humidityDiagnostic = ok ? "invalid_sample_values" : error;
    if (humidityFailures < 255) ++humidityFailures;
    if (humidityFailures <= 2 || millis() - lastHumidityDiagAt >= 15000) {
      Serial.printf("RH measurement FAILED: %s (T=%f, RH=%f)\n",
                    humidityDiagnostic, t, rh);
      lastHumidityDiagAt = millis();
    }
  }
}

