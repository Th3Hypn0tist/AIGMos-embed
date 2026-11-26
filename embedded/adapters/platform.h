#ifndef AIGMOS_PLATFORM_H
#define AIGMOS_PLATFORM_H
#include <stddef.h>
#include <stdint.h>
/* External adapter ABI. All operations return 0 on success, negative on error.
   Unavailable operations are NULL. Bus identifiers are composition-local. */
typedef struct {
    void *context;
    int (*gpio_mode)(void *,unsigned,unsigned);
    int (*gpio_read)(void *,unsigned,unsigned *);
    int (*gpio_write)(void *,unsigned,unsigned);
    int (*adc_read)(void *,unsigned,uint32_t *);
    int (*pwm_write)(void *,unsigned,uint32_t,uint32_t);
    int (*i2c_transfer)(void *,unsigned,uint8_t,const uint8_t *,size_t,uint8_t *,size_t);
    int (*spi_transfer)(void *,unsigned,const uint8_t *,uint8_t *,size_t);
    int (*uart_write)(void *,unsigned,const uint8_t *,size_t,size_t *);
    int (*uart_read)(void *,unsigned,uint8_t *,size_t,size_t *);
    uint64_t (*monotonic_us)(void *);
    void (*delay_us)(void *,uint32_t);
    int (*flash_read)(void *,uint32_t,uint8_t *,size_t);
    int (*flash_write)(void *,uint32_t,const uint8_t *,size_t);
    int (*flash_erase)(void *,uint32_t,size_t);
    int (*udp_send)(void *,const char *,uint16_t,const uint8_t *,size_t);
} aig_platform;
enum { AIG_GPIO_INPUT, AIG_GPIO_INPUT_PULLUP, AIG_GPIO_OUTPUT, AIG_GPIO_OPEN_DRAIN };
#endif
