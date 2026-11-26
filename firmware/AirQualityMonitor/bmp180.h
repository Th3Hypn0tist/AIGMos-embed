#pragma once
#include <Adafruit_BMP085.h>
Adafruit_BMP085 bmp180;
bool initBMP180() {
  uint8_t id=0;
  if (!i2cRead(0x77,0xD0,&id,1)||id!=0x55||!bmp180.begin(BMP085_STANDARD)) return false;
  pressureChip="BMP180"; bmpAddress=0x77; return true;
}
void readBMP180() {
  float t=bmp180.readTemperature(), p=bmp180.readPressure()/100.0f;
  if(isfinite(t)&&isfinite(p)&&p>=300&&p<=1200){bmpTemp=t;pressureHPa=p;lastBmpAt=millis();}
  else {bmpTemp=pressureHPa=NAN;}
}
