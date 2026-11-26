#pragma once
enum HumidityChip : uint8_t { HUM_NONE, HUM_HDC1080, HUM_SI7021, HUM_DHT11 };
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
uint32_t lastIngestAt = 0;
uint32_t sampleSequence = 0;
char bootId[17] = {0};
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

const char* pressureChip = "none";
