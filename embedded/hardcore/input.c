#include "input.h"
int aig_input_key(const char *k) {
    return k && k[0]=='#' && k[1]=='I' && k[2]==':' && k[3]!='\0';
}
int aig_input_write(aig_state *s,size_t slot,aig_value v) {
    if (!s || !s->slots || slot>=s->count || !aig_input_key(s->slots[slot].key)) return -1;
    return aig_state_set(s,slot,v);
}
