#pragma once
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
  if (Wire.requestFrom(addr, (uint8_t)len, (uint8_t)true) != len) return false;
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
  if (Wire.requestFrom(addr, (uint8_t)len, (uint8_t)true) != len) return false;
  for (size_t i = 0; i < len; ++i) data[i] = Wire.read();
  return true;
}

bool i2cReadDirect(uint8_t addr, uint8_t* data, size_t len) {
  if (Wire.requestFrom(addr, (uint8_t)len, (uint8_t)true) != len) return false;
  for (size_t i = 0; i < len; ++i) data[i] = Wire.read();
  return true;
}

uint16_t u16be(const uint8_t* p) { return (uint16_t(p[0]) << 8) | p[1]; }
uint16_t u16le(const uint8_t* p) { return (uint16_t(p[1]) << 8) | p[0]; }
int16_t s16le(const uint8_t* p) { return (int16_t)u16le(p); }

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

