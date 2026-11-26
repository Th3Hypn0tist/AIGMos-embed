#ifndef AIGMOS_INPUT_H
#define AIGMOS_INPUT_H
#include "state.h"
int aig_input_write(aig_state *state,size_t slot,aig_value value);
int aig_input_key(const char *key);
#endif
