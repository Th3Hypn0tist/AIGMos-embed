/* Temporary inventory firmware, no Wi-Fi association or application state. */
#include <Arduino.h>
#include <ESP8266WiFi.h>
#include "src/esp8266/adapter.h"
#include "src/probe/probe.h"

static aig_platform platform;
static aig_esp8266_config config;
static bool ready=false;

static void report(void *context,unsigned address,unsigned reg,int value) {
    bool *first=static_cast<bool *>(context);
    if(!*first)Serial.print(',');
    *first=false;
    Serial.printf("{\"address\":%u,\"register\":%u,\"value\":",address,reg);
    if(value<0)Serial.print("null");else Serial.print(value);
    Serial.print('}');
}
static void inventory() {
    if(!ready)return;
    unsigned levels[17]={0};
    for(size_t i=0;i<probe_gpio_count;++i) {
        unsigned pin=probe_gpio[i];
        if(pin>=17 || platform.gpio_mode(platform.context,pin,AIG_GPIO_INPUT) ||
           platform.gpio_read(platform.context,pin,&levels[pin])) {
            Serial.println("AIGPROBE_ERROR GPIO");return;
        }
    }
    uint8_t mac[6];
    WiFi.macAddress(mac);
    Serial.printf("AIGPROBE {\"version\":1,\"mac\":\"%02x:%02x:%02x:%02x:%02x:%02x\",\"i2c\":[",
                  mac[0],mac[1],mac[2],mac[3],mac[4],mac[5]);
    bool first=true;
    if(aig_probe_scan(&platform,0,probe_checks,probe_count,report,&first)) {
        Serial.println();return;
    }
    Serial.print("],\"gpio\":{");
    for(size_t i=0;i<probe_gpio_count;++i) {
        if(i)Serial.print(',');
        Serial.printf("\"%u\":%u",probe_gpio[i],levels[probe_gpio[i]]);
    }
    Serial.println("}}");
}
void setup() {
    config.sda=probe_sda;config.scl=probe_scl;
    WiFi.persistent(false);
    WiFi.mode(WIFI_OFF);
    ready=aig_esp8266_init(&platform,&config)==0;
    if(!ready){Serial.begin(115200);Serial.println("AIGPROBE_ERROR INIT");}
}
void loop() {
    inventory();
    delay(2000);
}
