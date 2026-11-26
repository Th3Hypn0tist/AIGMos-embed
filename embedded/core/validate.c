#include "validate.h"
static int same(const char *a,const char *b) {
    while (*a && *a==*b) { ++a; ++b; }
    return *a==*b;
}
int aig_validate(const aig_state *s,const aig_ter *t) {
    size_t i,j,k;
    if (!s || !t || !t->cs || (s->count && !s->slots) ||
        (t->trigger_count && !t->triggers) ||
        (t->event_count && (!t->events || !t->routes)) ||
        (t->cs->count && !t->cs->commands)) return -1;
#ifdef AIGMOS_ACCESSCORE
    if (!t->cs->authorize) return -1;
#endif
    for (i=0;i<s->count;++i) {
        const char *key=s->slots[i].key;
        if (!key || !*key) return -2;
        for (j=0;j<i;++j) if (same(key,s->slots[j].key)) return -2;
        if (s->slots[i].value.type<AIG_NULL || s->slots[i].value.type>AIG_REAL ||
            (s->slots[i].value.type==AIG_BOOL && s->slots[i].value.as.boolean>1)) return -2;
    }
    for (i=0;i<t->cs->count;++i) {
        const aig_command *c=&t->cs->commands[i];
        if (!c->name || !*c->name || !c->call) return -3;
        for (j=0;j<i;++j) if (same(c->name,t->cs->commands[j].name)) return -3;
    }
    for (i=0;i<t->trigger_count;++i) {
        const aig_trigger *tr=&t->triggers[i];
        if (tr->slot>=s->count || (tr->count && !tr->events)) return -4;
        for (j=0;j<tr->count;++j) if (tr->events[j]>=t->event_count) return -4;
    }
    for (i=0;i<t->event_count;++i) {
        const aig_event_route *r=&t->routes[i];
        if (t->events[i].pending>1 || (r->count && !r->runners)) return -5;
        for (j=0;j<r->count;++j) {
            const aig_runner *run=&r->runners[j];
            if (run->command>=t->cs->count || (run->argc && !run->args)) return -5;
            for (k=0;k<run->argc;++k) {
                const aig_value *v=&run->args[k];
                if (v->type<AIG_NULL || v->type>AIG_REAL ||
                    (v->type==AIG_BOOL && v->as.boolean>1)) return -5;
            }
        }
    }
    return 0;
}
