#include "ter.h"
int aig_ter_raise(aig_ter *t,size_t event) {
    if (!t || !t->events || event>=t->event_count) return -1;
    t->events[event].pending=1;
    return 0;
}
void aig_ter_on_change(void *context,size_t slot) {
    aig_ter *t=context; size_t i,j;
    if (!t || !t->triggers) return;
    for (i=0;i<t->trigger_count;++i) {
        const aig_trigger *tr=&t->triggers[i];
        if (tr->slot!=slot || !tr->events) continue;
        for (j=0;j<tr->count;++j) (void)aig_ter_raise(t,tr->events[j]);
    }
}
int aig_ter_step(aig_ter *t,size_t *executed) {
    size_t i,j; int first=0;
    if (!t || !executed || !t->cs || t->running || (t->event_count && (!t->events || !t->routes))) return -1;
    *executed=0;
    t->running=1;
    /* One bounded pass. Commands may raise events for a subsequent pass. */
    for (i=0;i<t->event_count;++i) {
        const aig_event_route *route=&t->routes[i];
        if (!t->events[i].pending) continue;
        t->events[i].pending=0;
        if (route->count && !route->runners) { if (!first) first=-1; continue; }
        for (j=0;j<route->count;++j) {
            const aig_runner *r=&route->runners[j];
            int rc=aig_cs_run(t->cs,r->command,r->args,r->argc);
            ++*executed;
            if (rc && !first) first=rc;
        }
    }
    t->running=0;
    return first;
}
