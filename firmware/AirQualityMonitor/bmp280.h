#pragma once
struct BMPCalibration {
  uint16_t T1, P1;
  int16_t T2, T3, P2, P3, P4, P5, P6, P7, P8, P9;
} bmpCal;

bool initBMP280() {
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
    bmpAddress = addr; pressureChip = "BMP280";
    Serial.printf("BMP280 detected at 0x%02X\n", addr);
    return true;
  }
  Serial.println("BMP280 not found");
  return false;
}

void readBMP280() {
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
    
  }
}

