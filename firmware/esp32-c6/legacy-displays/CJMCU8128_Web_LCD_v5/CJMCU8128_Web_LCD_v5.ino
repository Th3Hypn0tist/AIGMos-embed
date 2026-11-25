/*
 * CJMCU-8128 dashboard / ESP32-C6 / Arduino IDE
 * One-file firmware. Only Arduino-ESP32 bundled libraries are needed.
 * Sensors: CCS811, BMP280, HDC1080 OR Si7021 (autodetection).
 * HTTP: /  (dashboard), /api/sensors  (JSON)
 *
 * Hardware: CJMCU-8128 VCC=3.3V; CCS811 WAK=GND.
 * LCD 2004A: PCF8574 backpack at 0x27, powered at 3.3V.
 * LCD uses same SDA/SCL as sensors; no additional Arduino libraries.
 * v5 diagnostic: conservative 4-bit init + 5-second four-row text at boot.
 */
#include <Arduino.h>
#include <WiFi.h>
#include <WebServer.h>
#include <Wire.h>
#include <math.h>

// ---- CONFIGURATION ----------------------------------------------------------
const char* WIFI_SSID     = "IOT";
const char* WIFI_PASSWORD = "";  // Use "" for an open network.
// GPIO numbers (not the physical header pin positions).
constexpr int SDA_PIN     = 4;
constexpr int SCL_PIN     = 5;

// STATIC IP - EXAMPLE VALUES. Change to match your IOT Wi-Fi subnet/router.
// E.g. if your current DHCP address is 192.168.50.123 and gateway is
// 192.168.50.1, choose an available address such as 192.168.50.220.
const bool USE_STATIC_IP = true;
IPAddress STATIC_IP(192, 168, 1, 220);
IPAddress STATIC_GATEWAY(192, 168, 1, 1);
IPAddress STATIC_SUBNET(255, 255, 255, 0);
IPAddress STATIC_DNS(192, 168, 1, 1);

constexpr uint32_t I2C_HZ = 100000;
constexpr uint32_t SAMPLE_INTERVAL_MS = 2000;
constexpr uint8_t LCD_I2C_ADDR = 0x27;  // 20x4 PCF8574 LCD backpack
// -----------------------------------------------------------------------------

WebServer server(80);
bool lcdReady = false;

enum HumidityChip : uint8_t { HUM_NONE, HUM_HDC1080, HUM_SI7021 };
HumidityChip humidityChip = HUM_NONE;
const char* humidityDiagnostic = "not_initialized";
uint32_t lastHumidityRetry = 0;
uint32_t lastHumidityDiagAt = 0;
uint8_t humidityFailures = 0;
uint8_t bmpAddress = 0;
uint8_t ccsAddress = 0;
bool bmpReady = false;
bool ccsReady = false;
uint8_t ccsError = 0;
uint32_t ccsStartedAt = 0;
uint32_t lastSensorPoll = 0;
uint32_t lastWiFiRetry = 0;
bool wasWiFiConnected = false;
String foundDevices;

float ambientTemp = NAN;
float humidityRH = NAN;
float bmpTemp = NAN;
float pressureHPa = NAN;
int eco2 = -1;   // eCO2 is NOT directly measured CO2.
int tvoc = -1;
uint32_t lastClimateAt = 0;
uint32_t lastBmpAt = 0;
uint32_t lastGasAt = 0;

struct BMPCalibration {
  uint16_t T1, P1;
  int16_t T2, T3, P2, P3, P4, P5, P6, P7, P8, P9;
} bmpCal;

bool hasDevice(uint8_t addr) {
  Wire.beginTransmission(addr);
  return Wire.endTransmission() == 0;
}

bool i2cCommand(uint8_t addr, uint8_t command) {
  Wire.beginTransmission(addr);
  Wire.write(command);
  return Wire.endTransmission() == 0;
}

bool i2cWrite(uint8_t addr, uint8_t reg, const uint8_t* data, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  for (size_t i = 0; i < len; ++i) Wire.write(data[i]);
  return Wire.endTransmission() == 0;
}

bool i2cRead(uint8_t addr, uint8_t reg, uint8_t* data, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(false) != 0) return false;
  if (Wire.requestFrom(addr, len, true) != len) return false;
  for (size_t i = 0; i < len; ++i) data[i] = Wire.read();
  return true;
}

// HDC1080: a STOP between writing the register pointer and reading the
// response is more compatible with real CJMCU-8128 board revisions.
bool i2cReadStop(uint8_t addr, uint8_t reg, uint8_t* data, size_t len) {
  Wire.beginTransmission(addr);
  Wire.write(reg);
  if (Wire.endTransmission(true) != 0) return false;
  delay(2);
  if (Wire.requestFrom(addr, len, true) != len) return false;
  for (size_t i = 0; i < len; ++i) data[i] = Wire.read();
  return true;
}

bool i2cReadDirect(uint8_t addr, uint8_t* data, size_t len) {
  if (Wire.requestFrom(addr, len, true) != len) return false;
  for (size_t i = 0; i < len; ++i) data[i] = Wire.read();
  return true;
}

uint16_t u16be(const uint8_t* p) { return (uint16_t(p[0]) << 8) | p[1]; }
uint16_t u16le(const uint8_t* p) { return (uint16_t(p[1]) << 8) | p[0]; }
int16_t s16le(const uint8_t* p) { return (int16_t)u16le(p); }

// ---- HD44780 20x4 LCD via common PCF8574 I2C backpack ----------------------
// Standard adapter pin mapping: P0=RS, P1=RW, P2=EN, P3=backlight,
// P4..P7 = HD44780 D4..D7. No external LiquidCrystal library needed.
constexpr uint8_t LCD_RS = 0x01;
constexpr uint8_t LCD_EN = 0x04;
constexpr uint8_t LCD_LIGHT = 0x08;

bool lcdExpanderWrite(uint8_t value) {
  Wire.beginTransmission(LCD_I2C_ADDR);
  Wire.write(value | LCD_LIGHT);
  return Wire.endTransmission() == 0;
}

void lcdWrite4(uint8_t hiNibble, uint8_t flags) {
  // Standard PCF8574 backpack wiring. Keep RW=0 (write mode) on every write.
  const uint8_t value = (hiNibble & 0xF0) | (flags & LCD_RS);
  lcdExpanderWrite(value);                 // E low, prepare data and RS
  delayMicroseconds(50);
  lcdExpanderWrite(value | LCD_EN);        // E high
  delayMicroseconds(100);
  lcdExpanderWrite(value);                 // E low: LCD latches nibble
  delayMicroseconds(200);                  // generous margin for LCD clones
}

void lcdWrite8(uint8_t value, uint8_t flags) {
  lcdWrite4(value & 0xF0, flags);
  lcdWrite4((value << 4) & 0xF0, flags);
}

void lcdCommand(uint8_t cmd) {
  lcdWrite8(cmd, 0);
  if (cmd == 0x01 || cmd == 0x02) delay(2);
}

void lcdChar(char ch) { lcdWrite8((uint8_t)ch, LCD_RS); }

bool lcdBegin() {
  if (!hasDevice(LCD_I2C_ADDR)) {
    Serial.printf("LCD: no PCF8574 at 0x%02X; display disabled\n", LCD_I2C_ADDR);
    return false;
  }

  // Slow, conservative startup sequence for HD44780-compatible clones.
  // The PCF8574 ACK does NOT confirm that the LCD controller accepted data.
  delay(500);                            // let 3.3-V LCD and backpack settle
  if (!lcdExpanderWrite(0)) {
    Serial.println("LCD: expander write failed");
    return false;
  }
  delay(50);
  lcdWrite4(0x30, 0); delay(10);         // 8-bit reset nibble 1
  lcdWrite4(0x30, 0); delay(10);         // 8-bit reset nibble 2
  lcdWrite4(0x30, 0); delay(10);         // 8-bit reset nibble 3
  lcdWrite4(0x20, 0); delay(10);         // switch to 4-bit data transfer
  lcdCommand(0x28); delay(2);           // 4-bit, two controller lines, 5x8
  lcdCommand(0x08); delay(2);           // display off
  lcdCommand(0x01); delay(5);           // clear all DDRAM
  lcdCommand(0x06); delay(2);           // entry mode
  lcdCommand(0x0C); delay(2);           // display on, cursor off
  Serial.println("LCD: 0x27 ACK, conservative 4-bit init sent (not proof of LCD response)");
  return true;
}

void lcdWriteLine(uint8_t row, const char* text);

void lcdStartupTest() {
  if (!lcdReady) return;
  Serial.println("LCD: showing four-row ASCII test for 5 seconds");
  lcdWriteLine(0, "ROW1 0123456789 ABCD");
  lcdWriteLine(1, "ROW2 0123456789 ABCD");
  lcdWriteLine(2, "ROW3 0123456789 ABCD");
  lcdWriteLine(3, "ROW4 0123456789 ABCD");
  delay(5000);
}

void lcdWriteLine(uint8_t row, const char* text) {
  if (!lcdReady || row > 3) return;
  static char previous[4][21] = {{0}};
  char padded[21];
  memset(padded, ' ', 20);
  size_t count = strlen(text);
  if (count > 20) count = 20;
  memcpy(padded, text, count);
  padded[20] = '\0';
  if (memcmp(previous[row], padded, 21) == 0) return;

  // HD44780 20x4 row DDRAM addresses: 0x00, 0x40, 0x14, 0x54.
  static const uint8_t offsets[4] = {0x00, 0x40, 0x14, 0x54};
  lcdCommand(0x80 | offsets[row]);
  for (uint8_t i = 0; i < 20; ++i) lcdChar(padded[i]);
  memcpy(previous[row], padded, 21);
}

void refreshLCD() {
  if (!lcdReady) return;
  char line[48], temp[18], gas[18], rh[18], voc[18];
  const uint32_t now = millis();
  const bool climateFresh = lastClimateAt && (uint32_t)(now - lastClimateAt) < 10000;
  const bool bmpFresh = lastBmpAt && (uint32_t)(now - lastBmpAt) < 10000;
  const bool gasFresh = lastGasAt && (uint32_t)(now - lastGasAt) < 10000;

  // Row 1: temperature first, eCO2 second. Fits 20 characters for
  // ordinary 3-digit readings: "T 25.5C  eCO2 560ppm".
  const float t = climateFresh ? ambientTemp : (bmpFresh ? bmpTemp : NAN);
  if (isfinite(t)) snprintf(temp, sizeof(temp), "T %.1fC", t);
  else strcpy(temp, "T --.-C");
  if (gasFresh && eco2 >= 0) snprintf(gas, sizeof(gas), "%dppm", eco2);
  else strcpy(gas, "---");
  // Reduce separator to one space for four-digit eCO2 values.
  const char* separator = strlen(temp) + strlen(gas) + 7 <= 20 ? "  " : " ";
  snprintf(line, sizeof(line), "%s%seCO2 %s", temp, separator, gas);
  lcdWriteLine(0, line);

  // Row 2: relative humidity then TVOC.
  if (climateFresh && isfinite(humidityRH))
    snprintf(rh, sizeof(rh), "RH %.1f%%", humidityRH);
  else strcpy(rh, "RH --.-%");
  if (gasFresh && tvoc >= 0) snprintf(voc, sizeof(voc), "%dppb", tvoc);
  else strcpy(voc, "---");
  snprintf(line, sizeof(line), "%s TVOC %s", rh, voc);
  if (strlen(line) > 20) snprintf(line, sizeof(line), "%s TVOC%s", rh, voc);
  lcdWriteLine(1, line);

  // Row 3: pressure.
  if (bmpFresh && isfinite(pressureHPa))
    snprintf(line, sizeof(line), "PRES %.1fhPa", pressureHPa);
  else strcpy(line, "PRES ----.-hPa");
  lcdWriteLine(2, line);

  // Row 4: currently assigned IP (static or DHCP), not a hardcoded string.
  if (WiFi.status() == WL_CONNECTED) {
    const String ip = WiFi.localIP().toString();
    snprintf(line, sizeof(line), "IP %s", ip.c_str());
  } else {
    strcpy(line, "IP WiFi offline");
  }
  lcdWriteLine(3, line);
}
// -----------------------------------------------------------------------------

void scanI2C() {
  foundDevices = "";
  for (uint8_t addr = 8; addr < 120; ++addr) {
    if (!hasDevice(addr)) continue;
    char part[8];
    snprintf(part, sizeof(part), "0x%02X", addr);
    if (foundDevices.length()) foundDevices += " ";
    foundDevices += part;
  }
  Serial.printf("I2C scan: %s\n", foundDevices.c_str());
}

void initHumidity() {
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

void readHumidity() {
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

bool initBMP() {
  for (uint8_t addr : {uint8_t(0x76), uint8_t(0x77)}) {
    uint8_t id;
    if (!i2cRead(addr, 0xD0, &id, 1) || id != 0x58) continue;
    uint8_t c[24];
    if (!i2cRead(addr, 0x88, c, sizeof(c))) continue;
    bmpCal.T1 = u16le(c + 0);  bmpCal.T2 = s16le(c + 2);
    bmpCal.T3 = s16le(c + 4);  bmpCal.P1 = u16le(c + 6);
    bmpCal.P2 = s16le(c + 8);  bmpCal.P3 = s16le(c + 10);
    bmpCal.P4 = s16le(c + 12); bmpCal.P5 = s16le(c + 14);
    bmpCal.P6 = s16le(c + 16); bmpCal.P7 = s16le(c + 18);
    bmpCal.P8 = s16le(c + 20); bmpCal.P9 = s16le(c + 22);
    if (bmpCal.P1 == 0) return false;

    // Standby 1000 ms, filter off; temperature x1, pressure x1, normal mode.
    const uint8_t config = 0xA0;
    const uint8_t measure = 0x27;
    if (!i2cWrite(addr, 0xF5, &config, 1)) continue;
    if (!i2cWrite(addr, 0xF4, &measure, 1)) continue;
    bmpAddress = addr;
    Serial.printf("BMP280 detected at 0x%02X\n", addr);
    return true;
  }
  Serial.println("BMP280 not found");
  return false;
}

void readBMP() {
  if (!bmpReady) return;
  uint8_t d[6];
  if (!i2cRead(bmpAddress, 0xF7, d, sizeof(d))) {
    bmpTemp = NAN;
    pressureHPa = NAN;
    return;
  }
  const int32_t adcP = ((uint32_t)d[0] << 12) | ((uint32_t)d[1] << 4) | (d[2] >> 4);
  const int32_t adcT = ((uint32_t)d[3] << 12) | ((uint32_t)d[4] << 4) | (d[5] >> 4);
  if (adcP == 0x80000 || adcT == 0x80000) return;

  // Bosch BMP280 datasheet floating-point compensation using OTP coefficients.
  double var1 = ((double)adcT / 16384.0 - (double)bmpCal.T1 / 1024.0) * (double)bmpCal.T2;
  double var2 = ((double)adcT / 131072.0 - (double)bmpCal.T1 / 8192.0);
  var2 = var2 * var2 * (double)bmpCal.T3;
  const double tFine = var1 + var2;
  const double t = tFine / 5120.0;

  var1 = tFine / 2.0 - 64000.0;
  var2 = var1 * var1 * (double)bmpCal.P6 / 32768.0;
  var2 += var1 * (double)bmpCal.P5 * 2.0;
  var2 = var2 / 4.0 + (double)bmpCal.P4 * 65536.0;
  var1 = ((double)bmpCal.P3 * var1 * var1 / 524288.0 + (double)bmpCal.P2 * var1) / 524288.0;
  var1 = (1.0 + var1 / 32768.0) * (double)bmpCal.P1;
  if (fabs(var1) < 0.000001) return;

  double p = 1048576.0 - (double)adcP;
  p = (p - var2 / 4096.0) * 6250.0 / var1;
  var1 = (double)bmpCal.P9 * p * p / 2147483648.0;
  var2 = p * (double)bmpCal.P8 / 32768.0;
  p += (var1 + var2 + (double)bmpCal.P7) / 16.0;

  if (isfinite(t) && isfinite(p)) {
    bmpTemp = (float)t;
    pressureHPa = (float)(p / 100.0);
    lastBmpAt = millis();
    // Use the BMP temperature as a fallback if 0x40 is unavailable.
    if (!isfinite(ambientTemp)) ambientTemp = bmpTemp;
  }
}

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

void pollSensors() {
  readHumidity();
  readBMP();
  readCCS();
  Serial.printf("Temp: %.2f C | RH: %.1f %% | pressure: %.1f hPa | eCO2: %d ppm | TVOC: %d ppb\n",
                ambientTemp, humidityRH, pressureHPa, eco2, tvoc);
}

// ---------------------------- HTML dashboard --------------------------------
const char DASHBOARD[] PROGMEM = R"DASHBOARD(
<!doctype html><html lang="fi"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="theme-color" content="#090f1c"><title>CJMCU-8128 · Sensor dashboard</title>
<style>
:root{color-scheme:dark;--bg:#080d18;--panel:#101929;--border:#243349;--muted:#8d9cb2;--text:#eff5ff;--green:#55e0b2;--blue:#68b7ff;--amber:#ffbf66;--violet:#b6a0ff}
*{box-sizing:border-box}body{margin:0;background:radial-gradient(ellipse at 85% -15%,#153252 0%,transparent 48%),var(--bg);color:var(--text);font:15px/1.5 system-ui,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
.wrap{max-width:1160px;margin:0 auto;padding:36px 24px 60px}header{display:flex;align-items:flex-start;justify-content:space-between;gap:20px;margin-bottom:31px}
.eyebrow{color:var(--green);font-size:11px;letter-spacing:.19em;text-transform:uppercase;font-weight:750;margin:0 0 11px}
h1{font-size:clamp(27px,4vw,41px);line-height:1.13;letter-spacing:-.04em;margin:0 0 12px;font-weight:740}.sub{color:var(--muted);margin:0}
.badge{display:flex;align-items:center;gap:9px;background:#142438;border:1px solid #285048;color:#a0f1cc;border-radius:999px;padding:9px 14px;white-space:nowrap;font-size:12px;font-weight:700}
.dot{width:8px;height:8px;border-radius:100%;background:var(--green);box-shadow:0 0 13px #55e0b2}.badge.off{color:#fac0a8;border-color:#6b4435;background:#2e1e1d}.badge.off .dot{background:#f28c69;box-shadow:none}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card{min-width:0;background:linear-gradient(145deg,#121d2f,#0e1726);border:1px solid var(--border);border-radius:19px;padding:23px;box-shadow:0 12px 35px #02050b33;position:relative;overflow:hidden}
.card.primary{grid-column:span 2;min-height:268px;background:linear-gradient(125deg,#152f3b,#112132 50%,#121d2f)}
.card.primary:after{content:"";position:absolute;width:250px;height:250px;right:-80px;top:-100px;border-radius:50%;background:radial-gradient(circle,#35cbaa20,transparent 72%);pointer-events:none}
.card .label{font-weight:650;letter-spacing:.025em;color:#b0bfd1;font-size:12px;text-transform:uppercase}.reading{font-size:clamp(30px,4vw,47px);line-height:1.1;letter-spacing:-.05em;font-weight:750;margin:21px 0 4px;font-variant-numeric:tabular-nums}.primary .reading{font-size:clamp(49px,7vw,82px);margin-top:28px}
.unit{font-size:14px;color:var(--muted);font-weight:550;letter-spacing:0;margin-left:7px}.primary .unit{font-size:20px}.desc{color:var(--muted);font-size:12px;margin:10px 0 0}.accent{color:var(--green)}
.spark{display:block;width:100%;height:45px;overflow:visible;margin:22px 0 0}.spark polyline{fill:none;stroke:var(--blue);stroke-width:2.4;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke}.primary .spark polyline{stroke:var(--green)}
.meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:16px 0}.meta .card{padding:18px 20px;min-height:94px}.meta .label{font-size:10px}.meta .v{font-weight:720;margin-top:8px;font-size:15px;overflow-wrap:anywhere}
.section{font-size:12px;text-transform:uppercase;letter-spacing:.15em;color:#a1b2c8;margin:32px 0 14px;font-weight:700}
.sensors{display:flex;flex-wrap:wrap;gap:9px}.chip{border:1px solid var(--border);background:#101929;border-radius:8px;padding:9px 11px;color:#c5d4e6;font-size:12px}.chip b{color:var(--green);font-weight:700}.chip.missing b{color:#ffad8b}
footer{margin-top:26px;display:flex;justify-content:space-between;flex-wrap:wrap;gap:12px;color:#7d91a9;font-size:12px}footer a{color:#95c8ff;text-decoration:none}
@media(max-width:760px){.wrap{padding:25px 14px 40px}.grid{grid-template-columns:repeat(2,minmax(0,1fr));gap:11px}.card{padding:18px;border-radius:14px}.card.primary{grid-column:span 2;min-height:235px}.meta{grid-template-columns:1fr 1fr;gap:11px}header{flex-direction:column;margin-bottom:24px}}
@media(max-width:440px){.grid{grid-template-columns:1fr}.card.primary{grid-column:span 1}.reading{font-size:41px}.meta{grid-template-columns:1fr 1fr}}
</style></head><body><main class="wrap">
<header><div><p class="eyebrow">ESP32-C6 / ENVIRONMENT MONITOR</p><h1>CJMCU-8128 <span class="accent">Live</span></h1><p class="sub">Paikallinen sensoriseuranta · päivitys 2 sekunnin välein</p></div>
<div class="badge off" id="status"><span class="dot"></span><span id="status-text">Yhdistetään…</span></div></header>
<section class="grid">
 <article class="card primary"><div class="label">Ilmanlaatu · eCO₂</div><div class="reading"><span id="eco2">—</span><span class="unit">ppm</span></div><p class="desc" id="gas-note">CCS811:n laskennallinen CO₂-arvo, ei suora CO₂-mittaus.</p><svg class="spark" viewBox="0 0 300 45" preserveAspectRatio="none" id="plot-eco2"></svg></article>
 <article class="card"><div class="label">Haihtuvat yhdisteet</div><div class="reading"><span id="tvoc">—</span><span class="unit">ppb</span></div><p class="desc">TVOC · CCS811</p><svg class="spark" viewBox="0 0 300 45" preserveAspectRatio="none" id="plot-tvoc"></svg></article>
 <article class="card"><div class="label">Lämpötila</div><div class="reading"><span id="temperature">—</span><span class="unit">°C</span></div><p class="desc">Ilma-anturi / BMP280-varamittaus</p><svg class="spark" viewBox="0 0 300 45" preserveAspectRatio="none" id="plot-temperature"></svg></article>
 <article class="card"><div class="label">Ilmankosteus</div><div class="reading"><span id="humidity">—</span><span class="unit">%</span></div><p class="desc">Suhteellinen kosteus</p><svg class="spark" viewBox="0 0 300 45" preserveAspectRatio="none" id="plot-humidity"></svg></article>
 <article class="card"><div class="label">Ilmanpaine</div><div class="reading"><span id="pressure">—</span><span class="unit">hPa</span></div><p class="desc">BMP280 · paikallinen ilmanpaine</p><svg class="spark" viewBox="0 0 300 45" preserveAspectRatio="none" id="plot-pressure"></svg></article>
 </section>
 <section class="meta"><div class="card"><div class="label">Wi-Fi</div><div class="v" id="wifi">—</div></div><div class="card"><div class="label">IP-osoite</div><div class="v" id="ip">—</div></div><div class="card"><div class="label">Käynnissä</div><div class="v" id="uptime">—</div></div></section>
 <h2 class="section">Laitteiston tila</h2><div class="sensors"><div class="chip" id="chip-ccs">CCS811 <b>…</b></div><div class="chip" id="chip-bmp">BMP280 <b>…</b></div><div class="chip" id="chip-hum">Kosteusanturi <b>…</b></div></div>
 <footer><span id="updated">Odotetaan mittauksia…</span><span>I²C: <span id="i2c">—</span> · <a href="/api/sensors">JSON API</a></span></footer>
 </main>
<script>
const $=id=>document.getElementById(id), history={}, keys=['eco2','tvoc','temperature','humidity','pressure'];
for(const k of keys)history[k]=[];
function show(id,n,decimals=0){$(id).textContent=Number.isFinite(n)?n.toFixed(decimals):'—'}
function chip(id,name,active,details=''){
 const el=$(id);el.className='chip'+(active?'':' missing');
 el.innerHTML=name+' <b>'+(active?'ONLINE':'OFFLINE')+'</b>'+(details?' · '+details:'');
}
function chart(key,value){
 const h=history[key];if(Number.isFinite(value))h.push(value);if(h.length>42)h.shift();
 const svg=$('plot-'+key);if(h.length<2){svg.innerHTML='';return}
 const lo=Math.min(...h),hi=Math.max(...h),span=Math.max(hi-lo,0.01);
 const points=h.map((v,i)=>`${(i/(Math.max(h.length-1,1))*300).toFixed(1)},${(38-31*(v-lo)/span).toFixed(1)}`).join(' ');
 svg.innerHTML=`<polyline points="${points}"/>`;
}
async function refresh(){
 try{
  const response=await fetch('/api/sensors',{cache:'no-store'});
  if(!response.ok)throw Error('HTTP '+response.status);
  const d=await response.json();
  const st=$('status');st.classList.remove('off');$('status-text').textContent='LIVE · 2 s';
  show('temperature',d.temperature,1);show('humidity',d.humidity,1);
  show('pressure',d.pressure,1);show('eco2',d.eco2);show('tvoc',d.tvoc);
  for(const key of keys)chart(key,d[key]);
  $('wifi').textContent=d.wifi.connected?`${d.wifi.ssid} · ${d.wifi.rssi} dBm`:'Ei yhteyttä';
  $('ip').textContent=d.wifi.ip||'—';
  const seconds=d.uptime_s;$('uptime').textContent=`${Math.floor(seconds/3600)} h ${Math.floor(seconds%3600/60)} min`;
  chip('chip-ccs','CCS811',d.sensors.ccs811,d.ccs_error?`virhe 0x${d.ccs_error.toString(16).toUpperCase()}`:'');
  chip('chip-bmp','BMP280',d.sensors.bmp280);
  chip('chip-hum',d.sensors.humidity_chip||'Kosteusanturi',d.sensors.humidity,d.sensors.humidity?'':(d.humidity_diag||''));
  $('i2c').textContent=d.i2c||'Ei laitteita';
  $('gas-note').textContent=d.warmup_remaining_s>0?
     `CCS811 tasaantuu vielä noin ${Math.ceil(d.warmup_remaining_s/60)} min · eCO₂ on laskennallinen arvo.`:
     'CCS811:n laskennallinen CO₂-arvo, ei suora CO₂-mittaus.';
  $('updated').textContent=`Viimeisin yhteys ${new Date().toLocaleTimeString('fi-FI')} · arvot päivittyvät automaattisesti`;
 }catch(err){$('status').classList.add('off');$('status-text').textContent='Ei yhteyttä';$('updated').textContent='Yhteys palvelimeen katkesi: '+err.message;}
}
refresh();setInterval(refresh,2000);
</script></body></html>
)DASHBOARD";

String jsonFloat(float n, uint8_t decimals, bool available = true) {
  return (available && isfinite(n)) ? String(n, static_cast<unsigned int>(decimals)) : String("null");
}

String jsonInt(int n, bool available = true) {
  return (available && n >= 0) ? String(n) : String("null");
}

void handleAPI() {
  const uint32_t now = millis();
  const bool climateFresh = lastClimateAt && (uint32_t)(now - lastClimateAt) < 10000;
  const bool bmpFresh = lastBmpAt && (uint32_t)(now - lastBmpAt) < 10000;
  const bool gasFresh = lastGasAt && (uint32_t)(now - lastGasAt) < 10000;
  const bool connected = WiFi.status() == WL_CONNECTED;
  const char* humName = humidityChip == HUM_HDC1080 ? "HDC1080" :
                        humidityChip == HUM_SI7021 ? "Si7021" : "";
  const float temp = climateFresh ? ambientTemp : (bmpFresh ? bmpTemp : NAN);
  const uint32_t ccsRuntime = ccsReady ? (uint32_t)(now - ccsStartedAt) / 1000 : 0;
  const uint32_t warmup = ccsReady && ccsRuntime < 1200 ? 1200 - ccsRuntime : 0;

  String out;
  out.reserve(480);
  out += "{\"temperature\":" + jsonFloat(temp, 2);
  out += ",\"humidity\":" + jsonFloat(humidityRH, 2, climateFresh);
  out += ",\"humidity_diag\":\"" + String(humidityDiagnostic) + "\"";
  out += ",\"pressure\":" + jsonFloat(pressureHPa, 2, bmpFresh);
  out += ",\"bmp_temperature\":" + jsonFloat(bmpTemp, 2, bmpFresh);
  out += ",\"eco2\":" + jsonInt(eco2, gasFresh);
  out += ",\"tvoc\":" + jsonInt(tvoc, gasFresh);
  out += ",\"ccs_error\":" + String(ccsError);
  out += ",\"warmup_remaining_s\":" + String(warmup);
  out += ",\"uptime_s\":" + String(now / 1000);
  out += ",\"sensors\":{\"ccs811\":" + String(ccsReady ? "true" : "false");
  out += ",\"bmp280\":" + String(bmpReady ? "true" : "false");
  out += ",\"humidity\":" + String(climateFresh && isfinite(humidityRH) ? "true" : "false");
  out += ",\"humidity_chip\":\"" + String(humName) + "\"}";
  out += ",\"wifi\":{\"connected\":" + String(connected ? "true" : "false");
  out += ",\"ssid\":\"IOT\"";
  out += ",\"rssi\":" + String(connected ? WiFi.RSSI() : 0);
  out += ",\"ip\":\"" + (connected ? WiFi.localIP().toString() : String("")) + "\"}";
  out += ",\"i2c\":\"" + foundDevices + "\"}";

  server.sendHeader("Cache-Control", "no-store, no-cache, must-revalidate");
  server.send(200, "application/json; charset=utf-8", out);
}

void printNetworkAddress() {
  if (WiFi.status() != WL_CONNECTED) return;
  Serial.println("\n=== Wi-Fi connected ===");
  Serial.print("SSID: ");
  Serial.println(WiFi.SSID());
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());
  Serial.print("Dashboard: http://");
  Serial.println(WiFi.localIP());
  Serial.println("=======================");
}

void setup() {
  Serial.begin(115200);
  delay(400);
  Serial.println("\nCJMCU-8128 / ESP32-C6 / Web dashboard");

  Wire.begin(SDA_PIN, SCL_PIN, 50000);  // LCD diagnostic: slower bus, shared with sensors
  scanI2C();
  lcdReady = lcdBegin();
  lcdStartupTest();
  initHumidity();
  bmpReady = initBMP();
  ccsReady = initCCS();
  pollSensors();
  lastSensorPoll = millis();

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  if (USE_STATIC_IP) {
    if (WiFi.config(STATIC_IP, STATIC_GATEWAY, STATIC_SUBNET, STATIC_DNS)) {
      Serial.printf("Static IP configured: %s / gateway %s\n",
                    STATIC_IP.toString().c_str(), STATIC_GATEWAY.toString().c_str());
    } else {
      Serial.println("ERROR: Static IP configuration failed");
    }
  }
  if (strlen(WIFI_PASSWORD)) WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  else WiFi.begin(WIFI_SSID);
  Serial.printf("Connecting to Wi-Fi: %s", WIFI_SSID);
  const uint32_t start = millis();
  while (WiFi.status() != WL_CONNECTED && (uint32_t)(millis() - start) < 15000) {
    delay(300);
    Serial.print(".");
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    wasWiFiConnected = true;
    printNetworkAddress();
  } else {
    Serial.println("Wi-Fi not connected. Check credentials/2.4 GHz network.");
  }

  server.on("/", HTTP_GET, []() {
    server.sendHeader("Cache-Control", "no-store");
    server.send_P(200, "text/html; charset=utf-8", DASHBOARD);
  });
  server.on("/api/sensors", HTTP_GET, handleAPI);
  server.onNotFound([]() { server.send(404, "text/plain", "404 Not found"); });
  server.begin();
  Serial.println("WebServer listening on port 80");
  refreshLCD();
}

void loop() {
  server.handleClient();
  const uint32_t now = millis();
  if ((uint32_t)(now - lastSensorPoll) >= SAMPLE_INTERVAL_MS) {
    lastSensorPoll = now;
    pollSensors();
    refreshLCD();
  }
  if (humidityChip == HUM_NONE && (uint32_t)(now - lastHumidityRetry) >= 15000) {
    lastHumidityRetry = now;
    initHumidity();
  }
  const bool wifiConnected = WiFi.status() == WL_CONNECTED;
  if (wifiConnected != wasWiFiConnected) {
    wasWiFiConnected = wifiConnected;
    if (wifiConnected) printNetworkAddress();
    else Serial.println("Wi-Fi disconnected; reconnecting...");
    refreshLCD();
  }
  if (!wifiConnected && (uint32_t)(now - lastWiFiRetry) >= 10000) {
    lastWiFiRetry = now;
    WiFi.reconnect();
  }
  delay(2);
}