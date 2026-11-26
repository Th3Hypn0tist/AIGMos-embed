#ifndef AIGMOS_CS_H
#define AIGMOS_CS_H
#include "state.h"
typedef int (*aig_command_fn)(void *, const aig_value *, size_t);
typedef struct { const char *name; aig_command_fn call; void *context; } aig_command;
typedef struct { const aig_command *commands; size_t count; } aig_cs;
enum { AIG_CS_INVALID=-100, AIG_CS_UNKNOWN=-101 };
int aig_cs_find(const aig_cs *cs, const char *name, size_t *index);
int aig_cs_run(const aig_cs *cs, size_t index, const aig_value *args, size_t argc);
int aig_cs_execute(const aig_cs *cs, const char *name, const aig_value *args, size_t argc);
#endif
