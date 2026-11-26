#ifndef AIGMOS_ROUTINE_H
#define AIGMOS_ROUTINE_H
#include "cs.h"
typedef struct { size_t command; const aig_value *args; size_t argc; } aig_routine_step;
typedef struct { const aig_cs *cs; const aig_routine_step *steps; size_t count; uint8_t running; } aig_routine;
/* Register this handler under a name such as &venttiilit.kiinni. */
int aig_routine_call(void *context,const aig_value *args,size_t argc);
#endif
