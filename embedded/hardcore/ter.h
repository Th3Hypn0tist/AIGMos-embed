#ifndef AIGMOS_TER_H
#define AIGMOS_TER_H
#include "cs.h"
/* Event state is a single pending flag; bindings live in the composition. */
typedef struct { uint8_t pending; } aig_event;
typedef struct { size_t slot; const size_t *events; size_t count; } aig_trigger;
typedef struct { size_t command; const aig_value *args; size_t argc; } aig_runner;
typedef struct { const aig_runner *runners; size_t count; } aig_event_route;
typedef struct {
    const aig_cs *cs;
    const aig_trigger *triggers; size_t trigger_count;
    aig_event *events; const aig_event_route *routes; size_t event_count;
    uint8_t running;
} aig_ter;
int aig_ter_raise(aig_ter *ter,size_t event);
void aig_ter_on_change(void *context,size_t slot);
int aig_ter_step(aig_ter *ter,size_t *executed);
#endif
