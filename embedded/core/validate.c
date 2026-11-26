#include "validate.h"
static int same(const char *a,const char *b) {
    while (*a && *a==*b) { ++a; ++b; }
    return *a==*b;
}
static int valid_commands(const aig_cs *cs,const aig_ter_command *list,size_t count) {
    size_t i,j;
    if (count && !list) return 0;
    for (i=0;i<count;++i) {
        if (list[i].command>=cs->count || (list[i].argc && !list[i].args)) return 0;
        for (j=0;j<list[i].argc;++j) {
            const aig_value *v=&list[i].args[j];
            if (v->type<AIG_NULL || v->type>AIG_REAL ||
                (v->type==AIG_BOOL && v->as.boolean>1)) return 0;
        }
    }
    return 1;
}
int aig_validate(const aig_state *s,const aig_ter *t) {
    size_t i,j;
    if (!s || !t || !t->cs || (s->count && !s->slots) ||
        (t->trigger_count && !t->triggers) ||
        (t->event_count && !t->events) || (t->runner_count && !t->runners) ||
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
    for (i=0;i<t->trigger_count;++i)
        if (!t->triggers[i].condition || t->triggers[i].state>1) return -4;
    for (i=0;i<t->event_count;++i) {
        const aig_event *e=&t->events[i];
        if (e->trigger>=t->trigger_count || !valid_commands(t->cs,e->commands,e->count)) return -5;
    }
    for (i=0;i<t->runner_count;++i) {
        const aig_runner *r=&t->runners[i];
        if (r->state>1 || !valid_commands(t->cs,r->commands,r->count)) return -6;
    }
    return 0;
}
