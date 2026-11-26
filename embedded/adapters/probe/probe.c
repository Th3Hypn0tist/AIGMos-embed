#include "probe.h"
int aig_probe_scan(const aig_platform *p,unsigned bus,const aig_probe_check *checks,size_t count,aig_probe_report report,void *ctx) {
    size_t i;
    if (!p || !p->i2c_transfer || !report || (count && !checks)) return -1;
    for (i=0;i<count;++i) {
        uint8_t reg=(uint8_t)checks[i].reg,value=0;
        int rc;
        if (checks[i].address<8 || checks[i].address>119 || checks[i].reg>256) return -1;
        if (checks[i].reg==256)
            rc=p->i2c_transfer(p->context,bus,checks[i].address,0,0,0,0);
        else
            rc=p->i2c_transfer(p->context,bus,checks[i].address,&reg,1,&value,1);
        report(ctx,checks[i].address,checks[i].reg,rc?-1:value);
    }
    return 0;
}
