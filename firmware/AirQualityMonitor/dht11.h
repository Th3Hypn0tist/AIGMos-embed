#pragma once
#include <DHT.h>
DHT dht(DHT_PIN,DHT11);
bool initDHT11() {
  dht.begin(); delay(2100);
  float h=dht.readHumidity(),t=dht.readTemperature();
  if(!isfinite(h)||!isfinite(t))return false;
  humidityChip=HUM_DHT11;humidityDiagnostic="ok";return true;
}
void readDHT11(){
  float h=dht.readHumidity(),t=dht.readTemperature();
  if(isfinite(h)&&isfinite(t)&&h>=0&&h<=100){ambientTemp=t;humidityRH=h;lastClimateAt=millis();humidityDiagnostic="ok";}
  else{ambientTemp=humidityRH=NAN;humidityDiagnostic="dht_read_failed";}
}
