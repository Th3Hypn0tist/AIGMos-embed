#ifndef AIGMOS_STATE_H
#define AIGMOS_STATE_H
#include <stddef.h>
#include <stdint.h>
typedef enum { AIG_NULL, AIG_BOOL, AIG_INT, AIG_REAL } aig_type;
typedef struct { aig_type type; union { uint8_t boolean; int64_t integer; double real; } as; } aig_value;
typedef struct { const char *key; aig_value value; } aig_slot;
typedef void (*aig_change)(void *, size_t);
typedef struct { aig_slot *slots; size_t count; aig_change changed; void *context; } aig_state;
int aig_state_find(const aig_state *s, const char *key, size_t *index);
int aig_state_set(aig_state *s, size_t index, aig_value value);
int aig_state_get(const aig_state *s, size_t index, aig_value *value);
#endif
