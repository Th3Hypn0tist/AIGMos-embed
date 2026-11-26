#ifndef AIG_DHT11_H
#define AIG_DHT11_H
#include "../../adapters/platform.h"
#include "../../hardcore/input.h"
typedef struct { const aig_platform *platform;unsigned pin;uint64_t last_us;uint8_t sampled; } aig_dht11;
int aig_dht11_decode(const uint8_t bytes[5],double *temperature,double *humidity);
int aig_dht11_read(aig_dht11 *dev,double *temperature,double *humidity);
int aig_dht11_sample(aig_dht11 *dev,aig_state *state,size_t temperature_slot,size_t humidity_slot);
#endif
