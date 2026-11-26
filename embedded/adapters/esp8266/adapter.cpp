/* Optional ESP8266 Arduino-core adapter. No SDK headers enter the runtime. */
#include "adapter.h"
#include <Arduino.h>
#include <Wire.h>
#include <ESP8266WiFi.h>
#include <WiFiUdp.h>

static bool pin_ok(unsigned pin) {
    return pin==4 || pin==5 || pin==12 || pin==13 || pin==14 || pin==16;
}
static int mode(void *,unsigned pin,unsigned value) {
    if (!pin_ok(pin)) return -1;
    switch(value) {
    case AIG_GPIO_INPUT: pinMode(pin,INPUT);break;
    case AIG_GPIO_INPUT_PULLUP: if(pin==16)return -1;pinMode(pin,INPUT_PULLUP);break;
    case AIG_GPIO_OUTPUT: pinMode(pin,OUTPUT);break;
    case AIG_GPIO_OPEN_DRAIN: if(pin==16)return -1;pinMode(pin,OUTPUT_OPEN_DRAIN);break;
    default:return -1;
    }
    return 0;
}
static int read_pin(void *,unsigned pin,unsigned *value) {
    if(!pin_ok(pin)||!value)return -1;
    *value=digitalRead(pin)==HIGH;return 0;
}
static int write_pin(void *,unsigned pin,unsigned value) {
    if(!pin_ok(pin)||value>1)return -1;
    digitalWrite(pin,value?HIGH:LOW);return 0;
}
static int transfer(void *,unsigned bus,uint8_t address,const uint8_t *tx,size_t tn,uint8_t *rx,size_t rn) {
    if(bus!=0||address<8||address>119||tn>32||rn>32||(tn&&!tx)||(rn&&!rx))return -1;
    if(tn||!rn) {
        Wire.beginTransmission(address);
        if(tn&&Wire.write(tx,tn)!=tn){Wire.endTransmission(true);return -1;}
        if(Wire.endTransmission(rn==0)!=0)return -1;
    }
    if(rn) {
        if(Wire.requestFrom(address,(uint8_t)rn,(uint8_t)true)!=rn)return -1;
        for(size_t i=0;i<rn;++i){int v=Wire.read();if(v<0)return -1;rx[i]=(uint8_t)v;}
    }
    return 0;
}
/* Single-threaded caller; call at least once per 32-bit micros wrap. */
static uint64_t clock_us(void *) {
    static uint32_t last=0;static uint64_t high=0;
    uint32_t now=micros();
    if(now<last)high+=UINT64_C(1)<<32;
    last=now;return high+now;
}
static void wait_us(void *,uint32_t us) {
    while(us>=1000){delay(1);us-=1000;}
    if(us)delayMicroseconds(us);
}
static int uart_write(void *,unsigned bus,const uint8_t *data,size_t count,size_t *done) {
    if(bus||!done||(count&&!data))return -1;
    *done=Serial.write(data,count);return *done==count?0:-1;
}
static int uart_read(void *,unsigned bus,uint8_t *data,size_t count,size_t *done) {
    if(bus||!done||(count&&!data))return -1;
    *done=0;
    while(*done<count&&Serial.available()){int v=Serial.read();if(v<0)break;data[(*done)++]=(uint8_t)v;}
    return 0;
}
static int udp(void *,const char *host,uint16_t port,const uint8_t *data,size_t count) {
    if(!host||!port||!data||!count||count>1472||WiFi.status()!=WL_CONNECTED)return -1;
    IPAddress ip;if(!ip.fromString(host))return -1;
    WiFiUDP socket;
    if(!socket.beginPacket(ip,port))return -1;
    if(socket.write(data,count)!=count){socket.stop();return -1;}
    int rc=socket.endPacket();socket.stop();return rc==1?0:-1;
}
int aig_esp8266_init(aig_platform *p,aig_esp8266_config *c) {
    if(!p||!c||!pin_ok(c->sda)||!pin_ok(c->scl)||c->sda==c->scl||c->sda==16||c->scl==16)return -1;
    *p=aig_platform{};
    p->context=c;p->gpio_mode=mode;p->gpio_read=read_pin;p->gpio_write=write_pin;
    p->i2c_transfer=transfer;p->monotonic_us=clock_us;p->delay_us=wait_us;
    p->uart_write=uart_write;p->uart_read=uart_read;p->udp_send=udp;
    Wire.begin(c->sda,c->scl);Wire.setClock(100000);Serial.begin(115200);
    return 0;
}
