#include "routine.h"
int aig_routine_call(void *context,const aig_value *args,size_t argc) {
    aig_routine *r=context; size_t i; int rc=0;
    (void)args;
    if (!r || !r->cs || r->running || argc || (r->count && !r->steps)) return AIG_CS_INVALID;
    r->running=1;
    for (i=0;i<r->count;++i) {
        const aig_routine_step *s=&r->steps[i];
        rc=aig_cs_run(r->cs,s->command,s->args,s->argc);
        if (rc) break;
    }
    r->running=0;
    return rc;
}
