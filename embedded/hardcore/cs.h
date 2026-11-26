#ifndef AIGMOS_CS_H
#define AIGMOS_CS_H
#include "state.h"
typedef int (*aig_command_fn)(void *, const aig_value *, size_t);
typedef struct { const char *name; aig_command_fn call; void *context; } aig_command;
#ifdef AIGMOS_ACCESSCORE
typedef int (*aig_access_fn)(void *, const char *, const aig_value *, size_t);
#endif
typedef struct { const aig_command *commands; size_t count;
#ifdef AIGMOS_ACCESSCORE
    aig_access_fn authorize; void *access_context;
#endif
} aig_cs;
enum { AIG_CS_INVALID=-100, AIG_CS_UNKNOWN=-101, AIG_CS_DENIED=-102 };
int aig_cs_find(const aig_cs *cs, const char *name, size_t *index);
int aig_cs_run(const aig_cs *cs, size_t index, const aig_value *args, size_t argc);
int aig_cs_execute(const aig_cs *cs, const char *name, const aig_value *args, size_t argc);
#endif
