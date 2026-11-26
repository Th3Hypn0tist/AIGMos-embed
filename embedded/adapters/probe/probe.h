#ifndef AIG_PROBE_H
#define AIG_PROBE_H
#include "../platform.h"
#ifdef __cplusplus
extern "C" {
#endif
typedef struct { uint8_t address; uint16_t reg; } aig_probe_check;
/* reg 256 = address-only transfer. Negative value = no response. */
typedef void (*aig_probe_report)(void *,unsigned,unsigned,int);
int aig_probe_scan(const aig_platform *,unsigned,const aig_probe_check *,size_t,aig_probe_report,void *);
extern const unsigned probe_sda,probe_scl,probe_gpio[];
extern const aig_probe_check probe_checks[];
extern const size_t probe_count,probe_gpio_count;
#ifdef __cplusplus
}
#endif
#endif
