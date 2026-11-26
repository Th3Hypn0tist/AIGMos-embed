#include "dht11.h"
int aig_dht11_decode(const uint8_t b[5],double *t,double *h) {
    if (!b || !t || !h || (uint8_t)(b[0]+b[1]+b[2]+b[3])!=b[4] ||
        b[1]>9 || b[3]>9 || b[0]>100 || b[2]>50 || (b[0]==100 && b[1]) ||
        (b[2]==50 && b[3])) return -1;
    *h=b[0]+b[1]/10.0;*t=b[2]+b[3]/10.0;return 0;
}
static int pulse(aig_dht11 *d,unsigned level,uint32_t *width) {
    const aig_platform *p=d->platform;
    uint64_t start=p->monotonic_us(p->context),elapsed;
    unsigned value,i;
    for (i=0;i<10000;++i) {
        if (p->gpio_read(p->context,d->pin,&value)) return -1;
        elapsed=p->monotonic_us(p->context)-start;
        if (elapsed>120) return -1;
        if (value!=level) { *width=(uint32_t)elapsed;return 0; }
    }
    return -1;
}
int aig_dht11_read(aig_dht11 *d,double *t,double *h) {
    const aig_platform *p;uint64_t now;uint32_t w;uint8_t b[5]={0};unsigned i;
    if (!d || !(p=d->platform) || !p->gpio_mode || !p->gpio_write || !p->gpio_read ||
        !p->monotonic_us || !p->delay_us || !t || !h) return -1;
    now=p->monotonic_us(p->context);
    if (d->sampled && now-d->last_us<2000000) return -1;
    d->sampled=1;d->last_us=now;
    if (p->gpio_write(p->context,d->pin,0) || p->gpio_mode(p->context,d->pin,AIG_GPIO_OPEN_DRAIN)) goto fail;
    p->delay_us(p->context,20000);
    if (p->gpio_mode(p->context,d->pin,AIG_GPIO_INPUT_PULLUP)) goto fail;
    if (pulse(d,1,&w) || pulse(d,0,&w) || w<50 || pulse(d,1,&w) || w<50) goto fail;
    for (i=0;i<40;++i) {
        if (pulse(d,0,&w) || w<25 || pulse(d,1,&w) || w<10 || w>100) goto fail;
        b[i/8]=(uint8_t)((b[i/8]<<1)|(w>=50));
    }
    return aig_dht11_decode(b,t,h);
fail:
    (void)p->gpio_mode(p->context,d->pin,AIG_GPIO_INPUT_PULLUP);
    return -1;
}
int aig_dht11_sample(aig_dht11 *d,aig_state *s,size_t ts,size_t hs) {
    double t,h;aig_value a={AIG_NULL,{0}},b={AIG_NULL,{0}};int rc;
    if (!s || !s->slots || ts>=s->count || hs>=s->count || ts==hs ||
        !aig_input_key(s->slots[ts].key) || !aig_input_key(s->slots[hs].key)) return -1;
    rc=aig_dht11_read(d,&t,&h);
    if (!rc) { a.type=AIG_REAL;a.as.real=t;b.type=AIG_REAL;b.as.real=h; }
    if (aig_input_write(s,ts,a)<0 || aig_input_write(s,hs,b)<0) return -1;
    return rc;
}
