#include "bmp180.h"
static int read_reg(aig_bmp180 *d,uint8_t reg,uint8_t *out,size_t n) {
    return d->platform->i2c_transfer(d->platform->context,d->bus,d->address,&reg,1,out,n);
}
static int write_reg(aig_bmp180 *d,uint8_t reg,uint8_t value) {
    uint8_t data[]={reg,value};
    return d->platform->i2c_transfer(d->platform->context,d->bus,d->address,data,2,0,0);
}
static int32_t u16(const uint8_t *p) { return (int32_t)p[0]*256+p[1]; }
static int32_t s16(const uint8_t *p) { int32_t n=u16(p);return n>=32768?n-65536:n; }
/* Defined arithmetic right shift, including negative calibration values. */
static int64_t shift(int64_t n,unsigned bits) {
    int64_t divisor=(int64_t)1<<bits;
    return n>=0?n/divisor:-((-n+divisor-1)/divisor);
}
int aig_bmp180_init(aig_bmp180 *d) {
    uint8_t id,cal[22]; size_t i; unsigned nonzero=0,not_ff=0;
    if (!d) return -1;
    d->ready=0;
    if (!d->platform || !d->platform->i2c_transfer || !d->platform->delay_us || d->address!=0x77) return -1;
    if (read_reg(d,0xd0,&id,1) || id!=0x55 || read_reg(d,0xaa,cal,sizeof cal)) return -1;
    for (i=0;i<sizeof cal;++i) { nonzero|=cal[i];not_ff|=(unsigned)(cal[i]^0xff); }
    if (!nonzero || !not_ff) return -1;
    d->ac1=s16(cal);d->ac2=s16(cal+2);d->ac3=s16(cal+4);
    d->ac4=u16(cal+6);d->ac5=u16(cal+8);d->ac6=u16(cal+10);
    d->b1=s16(cal+12);d->b2=s16(cal+14);d->mb=s16(cal+16);
    d->mc=s16(cal+18);d->md=s16(cal+20);
    if (!d->ac4 || !d->ac5 || !d->ac6) return -1;
    d->ready=1;return 0;
}
/* BMP180 integer compensation, OSS=0. Intermediate values widened. */
int aig_bmp180_compensate(const aig_bmp180 *d,int32_t ut,int32_t up,int32_t *temp,int32_t *pressure) {
    int64_t x1,x2,x3,b3,b4,b5,b6,b7,p,t;
    if (!d || !d->ready || !temp || !pressure || ut<0 || ut>65535 || up<0 || up>65535) return -1;
    x1=shift(((int64_t)ut-d->ac6)*d->ac5,15);
    if (!(x1+d->md)) return -1;
    x2=((int64_t)d->mc*2048)/(x1+d->md);
    b5=x1+x2;t=shift(b5+8,4);
    if (t < -400 || t > 850) return -1;
    b6=b5-4000;
    x1=shift(d->b2*shift(b6*b6,12),11);
    x2=shift(d->ac2*b6,11);
    x3=x1+x2;b3=shift((int64_t)d->ac1*4+x3+2,2);
    x1=shift(d->ac3*b6,13);
    x2=shift(d->b1*shift(b6*b6,12),16);
    x3=shift(x1+x2+2,2);
    b4=shift((int64_t)d->ac4*(x3+32768),15);
    if (b4<=0 || up<b3) return -1;
    b7=((int64_t)up-b3)*50000;
    p=(b7*2)/b4;
    if (p<10000 || p>200000) return -1;
    x1=shift(p,8);x1=shift(x1*x1*3038,16);
    x2=shift(-7357*p,16);
    p+=shift(x1+x2+3791,4);
    if (p<30000 || p>110000) return -1;
    *temp=(int32_t)t;*pressure=(int32_t)p;return 0;
}
int aig_bmp180_read(aig_bmp180 *d,double *temperature,double *pressure) {
    uint8_t raw[2];int32_t ut,t,p;
    if (!d || !d->ready || !temperature || !pressure) return -1;
    if (write_reg(d,0xf4,0x2e)) return -1;
    d->platform->delay_us(d->platform->context,5000);
    if (read_reg(d,0xf6,raw,2)) return -1;
    ut=u16(raw);
    if (write_reg(d,0xf4,0x34)) return -1;
    d->platform->delay_us(d->platform->context,5000);
    if (read_reg(d,0xf6,raw,2) || aig_bmp180_compensate(d,ut,u16(raw),&t,&p)) return -1;
    *temperature=t/10.0;*pressure=p/100.0;return 0;
}
int aig_bmp180_sample(aig_bmp180 *d,aig_state *s,size_t ts,size_t ps) {
    double t,p; aig_value a={AIG_NULL,{0}},b={AIG_NULL,{0}};int rc;
    if (!s || !s->slots || ts>=s->count || ps>=s->count || ts==ps ||
        !aig_input_key(s->slots[ts].key) || !aig_input_key(s->slots[ps].key)) return -1;
    rc=aig_bmp180_read(d,&t,&p);
    if (!rc) { a.type=AIG_REAL;a.as.real=t;b.type=AIG_REAL;b.as.real=p; }
    if (aig_input_write(s,ts,a)<0 || aig_input_write(s,ps,b)<0) return -1;
    return rc;
}
