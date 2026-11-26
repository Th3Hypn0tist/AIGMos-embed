#include "cs.h"
static int same(const char *a,const char *b) {
    if (!a || !b) return 0;
    while (*a && *a==*b) { ++a; ++b; }
    return *a==*b;
}
int aig_cs_find(const aig_cs *cs,const char *name,size_t *index) {
    size_t i;
    if (!cs || !name || !*name || !index || (cs->count && !cs->commands)) return AIG_CS_INVALID;
    for (i=0;i<cs->count;++i) if (same(cs->commands[i].name,name)) { *index=i; return 0; }
    return AIG_CS_UNKNOWN;
}
int aig_cs_run(const aig_cs *cs,size_t index,const aig_value *args,size_t argc) {
    if (!cs || !cs->commands || index>=cs->count || !cs->commands[index].call || (argc && !args)) return AIG_CS_INVALID;
    return cs->commands[index].call(cs->commands[index].context,args,argc);
}
int aig_cs_execute(const aig_cs *cs,const char *name,const aig_value *args,size_t argc) {
    size_t i; int rc=aig_cs_find(cs,name,&i);
    return rc ? rc : aig_cs_run(cs,i,args,argc);
}
