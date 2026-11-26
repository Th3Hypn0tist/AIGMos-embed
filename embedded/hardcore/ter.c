#include "ter.h"
static int valid(const aig_ter *t) {
    return t && t->cs && (!t->trigger_count || t->triggers) &&
        (!t->event_count || t->events) && (!t->runner_count || t->runners);
}
int aig_ter_evaluate(aig_ter *t,const aig_state *s) {
    size_t i; int first=0;
    if (!valid(t) || !s || t->running) return -1;
    for (i=0;i<t->trigger_count;++i) {
        aig_trigger *tr=&t->triggers[i];
        int rc=tr->condition ? tr->condition(tr->context,s) : -1;
        tr->state=(uint8_t)(rc==1);
        if (rc!=0 && rc!=1 && !first) first=rc<0?rc:-1;
    }
    return first;
}
int aig_ter_runner_set(aig_ter *t,size_t i,uint8_t state) {
    if (!valid(t) || i>=t->runner_count || state>1) return -1;
    t->runners[i].state=state;
    return 0;
}
static int commands(const aig_cs *cs,const aig_ter_command *list,size_t count,size_t *executed) {
    size_t i; int first=0;
    if (count && !list) return -1;
    for (i=0;i<count;++i) {
        int rc=aig_cs_run(cs,list[i].command,list[i].args,list[i].argc);
        ++*executed;
        if (rc && !first) first=rc;
    }
    return first;
}
int aig_ter_step(aig_ter *t,size_t *executed) {
    size_t i; int first=0;
    if (!valid(t) || !executed || t->running) return -1;
    *executed=0; t->running=1;
    /* Provisional level-driven policy: every event observes its trigger state.
       No event-owned pending flag; evaluate and step are separate operations. */
    for (i=0;i<t->event_count;++i) {
        const aig_event *e=&t->events[i]; int rc;
        if (e->trigger>=t->trigger_count) { if (!first) first=-1; continue; }
        if (t->triggers[e->trigger].state!=1) continue;
        rc=commands(t->cs,e->commands,e->count,executed);
        if (rc && !first) first=rc;
    }
    for (i=0;i<t->runner_count;++i) {
        aig_runner *r=&t->runners[i]; int rc;
        if (r->state!=1) continue;
        rc=commands(t->cs,r->commands,r->count,executed);
        if (rc && !first) first=rc;
    }
    t->running=0; return first;
}
