#include <Arduino.h>
#include <Wire.h>
#include <math.h>
#if defined(ESP8266)
#include <ESP8266WiFi.h>
#define PLATFORM "ESP8266"
#else
#include <WiFi.h>
#include <esp_system.h>
#define PLATFORM "ESP32-C6"
#endif
#include "config.h"
#include "state.h"
#include "i2c.h"
#include "osc.h"
#if ENABLE_BMP180
#include "bmp180.h"
#endif
#if ENABLE_BMP280
#include "bmp280.h"
#endif
#if ENABLE_DHT11
#include "dht11.h"
#endif
#if ENABLE_HUMIDITY_I2C
#include "humidity_i2c.h"
#endif
#if ENABLE_CCS811
#include "ccs811.h"
#endif
char nodeId[13]={};
uint64_t sequence=0, uptime=0;
uint32_t previousMillis=0;
const char* humidityName(){
  switch(humidityChip){case HUM_DHT11:return "DHT11";case HUM_HDC1080:return "HDC1080";case HUM_SI7021:return "Si7021";default:return "none";}
}
void detect(){
#if ENABLE_BMP280
  bmpReady=initBMP280();
#endif
#if ENABLE_BMP180
  if(!bmpReady)bmpReady=initBMP180();
#endif
#if ENABLE_HUMIDITY_I2C
  initHumidityI2C();
#endif
#if ENABLE_DHT11
  if(humidityChip==HUM_NONE)initDHT11();
#endif
#if ENABLE_CCS811
  ccsReady=initCCS();
#endif
}
void poll(){
#if ENABLE_BMP280
  if(bmpReady&&!strcmp(pressureChip,"BMP280"))readBMP280();
#endif
#if ENABLE_BMP180
  if(bmpReady&&!strcmp(pressureChip,"BMP180"))readBMP180();
#endif
#if ENABLE_DHT11
  if(humidityChip==HUM_DHT11)readDHT11();
#endif
#if ENABLE_HUMIDITY_I2C
  if(humidityChip==HUM_HDC1080||humidityChip==HUM_SI7021)readHumidityI2C();
#endif
#if ENABLE_CCS811
  readCCS();
#endif
  Serial.printf("AQM %s %s %s %s T=%.2f RH=%.2f P=%.2f\n",nodeId,pressureChip,humidityName(),ccsReady?"CCS811":"none",bmpTemp,humidityRH,pressureHPa);
}
bool fresh(uint32_t t){return t&&millis()-t<10000;}
void sendSample(){
  OscMessage m;
  m.i(1);m.s(nodeId);m.s(PLATFORM);m.s("2.0.0");m.s(bootId);m.h(sequence++);m.h(uptime);
  m.f(fresh(lastClimateAt)?ambientTemp:NAN);m.f(fresh(lastBmpAt)?bmpTemp:NAN);
  m.f(fresh(lastClimateAt)?humidityRH:NAN);m.f(fresh(lastBmpAt)?pressureHPa:NAN);
  m.optionalInt(fresh(lastGasAt)?eco2:-1);m.optionalInt(fresh(lastGasAt)?tvoc:-1);
  m.boolean(ccsReady&&millis()-ccsStartedAt<1200000);m.i(ccsError);
  m.s(humidityName());m.s(humidityDiagnostic);m.i(WiFi.RSSI());
  Serial.println(m.send("/aqm/sample")?"OSC sent":"OSC failed");
}
void setup(){
  Serial.begin(115200);delay(300);
  WiFi.mode(WIFI_STA);
  uint8_t mac[6];WiFi.macAddress(mac);
  snprintf(nodeId,sizeof(nodeId),"%02x%02x%02x%02x%02x%02x",mac[0],mac[1],mac[2],mac[3],mac[4],mac[5]);
#if defined(ESP8266)
  uint32_t a=ESP.random(),b=ESP.random();
#else
  uint32_t a=esp_random(),b=esp_random();
#endif
  snprintf(bootId,sizeof(bootId),"%08lx%08lx",(unsigned long)a,(unsigned long)b);
  Wire.begin(SDA_PIN,SCL_PIN);Wire.setClock(100000);scanI2C();detect();
  if(!PROBE_ONLY){
    IPAddress ip,gw,mask;
    if(ip.fromString(STATIC_IP)&&gw.fromString(STATIC_GATEWAY)&&mask.fromString(STATIC_SUBNET))WiFi.config(ip,gw,mask);
    WiFi.setAutoReconnect(true);WiFi.begin(WIFI_SSID,WIFI_PASSWORD);
  }
}
void loop(){
  uint32_t now=millis();uptime+=(uint32_t)(now-previousMillis);previousMillis=now;
  if(now-lastSensorPoll>=5000){lastSensorPoll=now;poll();if(!PROBE_ONLY&&WiFi.status()==WL_CONNECTED)sendSample();}
  delay(5);
}
