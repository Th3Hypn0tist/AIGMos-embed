#include "../hardcore/state.h"
#include <assert.h>
static void change(void *ctx,size_t i) { assert(i==0); ++*(int *)ctx; }
int main(void) {
    int n=0; size_t i; aig_value v={AIG_INT,{.integer=42}}, out;
    aig_slot slots[]={{"#I:sensor",{AIG_NULL,{0}}}};
    aig_state s={slots,1,change,&n};
    assert(aig_state_find(&s,"#I:sensor",&i)==0 && i==0);
    assert(aig_state_find(&s,"missing",&i)==-1);
    assert(aig_state_set(&s,0,v)==1 && n==1);
    assert(aig_state_set(&s,0,v)==0 && n==1);
    assert(aig_state_get(&s,0,&out)==0 && out.as.integer==42);
    assert(aig_state_set(&s,1,v)==-1);
    return 0;
}
