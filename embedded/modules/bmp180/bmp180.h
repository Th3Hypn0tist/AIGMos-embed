#ifndef AIG_BMP180_H
#define AIG_BMP180_H
#include "../../adapters/platform.h"
#include "../../hardcore/input.h"
typedef struct {
    const aig_platform *platform;
    unsigned bus;
    uint8_t address;
    int32_t ac1,ac2,ac3,ac4,ac5,ac6,b1,b2,mb,mc,md;
    uint8_t ready;
} aig_bmp180;
int aig_bmp180_init(aig_bmp180 *dev);
int aig_bmp180_compensate(const aig_bmp180 *dev,int32_t ut,int32_t up,int32_t *temp_tenths,int32_t *pressure_pa);
int aig_bmp180_read(aig_bmp180 *dev,double *temperature,double *pressure);
int aig_bmp180_sample(aig_bmp180 *dev,aig_state *state,size_t temperature_slot,size_t pressure_slot);
#endif
