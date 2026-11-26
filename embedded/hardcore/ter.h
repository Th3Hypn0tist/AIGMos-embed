#ifndef AIGMOS_TER_H
#define AIGMOS_TER_H
#include "cs.h"
/* Conditions belong to TER, not ExpressionEngine. Return 0/1 or negative error. */
typedef int (*aig_condition)(void *,const aig_state *);
typedef struct { aig_condition condition; void *context; uint8_t state; } aig_trigger;
typedef struct { size_t command; const aig_value *args; size_t argc; } aig_ter_command;
typedef struct { size_t trigger; const aig_ter_command *commands; size_t count; } aig_event;
typedef struct { uint8_t state; const aig_ter_command *commands; size_t count; } aig_runner;
typedef struct {
    const aig_cs *cs;
    aig_trigger *triggers; size_t trigger_count;
    const aig_event *events; size_t event_count;
    aig_runner *runners; size_t runner_count;
    uint8_t running;
} aig_ter;
int aig_ter_evaluate(aig_ter *ter,const aig_state *state);
int aig_ter_runner_set(aig_ter *ter,size_t runner,uint8_t state);
int aig_ter_step(aig_ter *ter,size_t *executed);
#endif
