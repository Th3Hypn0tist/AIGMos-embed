#ifndef AIG_ESP8266_ADAPTER_H
#define AIG_ESP8266_ADAPTER_H
#include "../platform.h"
#ifdef __cplusplus
extern "C" {
#endif
/* One bus; pin assignments supplied by the composition. */
typedef struct { unsigned sda,scl; } aig_esp8266_config;
int aig_esp8266_init(aig_platform *,aig_esp8266_config *);
#ifdef __cplusplus
}
#endif
#endif
