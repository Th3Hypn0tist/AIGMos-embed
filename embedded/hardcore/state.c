#include "state.h"
static int same(const char *a, const char *b) {
    if (!a || !b) return 0;
    while (*a && *a == *b) { ++a; ++b; }
    return *a == *b;
}
int aig_state_find(const aig_state *s, const char *key, size_t *index) {
    size_t i;
    if (!s || !key || !index || !s->slots) return -1;
    for (i=0;i<s->count;++i) if (same(s->slots[i].key,key)) { *index=i; return 0; }
    return -1;
}
int aig_state_get(const aig_state *s, size_t i, aig_value *v) {
    if (!s || !s->slots || !v || i>=s->count) return -1;
    *v=s->slots[i].value; return 0;
}
int aig_state_set(aig_state *s, size_t i, aig_value v) {
    aig_value old;
    int equal=0;
    if (!s || !s->slots || i>=s->count || v.type<AIG_NULL || v.type>AIG_REAL) return -1;
    if (v.type==AIG_BOOL && v.as.boolean>1) return -1;
    old=s->slots[i].value;
    if (old.type==v.type) switch(v.type) {
        case AIG_NULL: equal=1; break;
        case AIG_BOOL: equal=old.as.boolean==v.as.boolean; break;
        case AIG_INT: equal=old.as.integer==v.as.integer; break;
        case AIG_REAL: equal=old.as.real==v.as.real; break;
    }
    if (equal) return 0;
    s->slots[i].value=v;
    if (s->changed) s->changed(s->context,i);
    return 1;
}
