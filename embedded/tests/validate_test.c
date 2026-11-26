#include "../core/validate.h"
#include "../hardcore/input.h"
#include <assert.h>
static int command(void *c,const aig_value *v,size_t n) { (void)c;(void)v;(void)n;return 0; }
int main(void) {
    aig_slot slots[]={{"#I:sensor",{AIG_NULL,{0}}},{"internal",{AIG_NULL,{0}}}};
    aig_state s={slots,2,0,0};
    const aig_command commands[]={{"um.test",command,0}};
    const aig_cs cs={commands,1};
    aig_event events[]={{0}};
    const aig_runner runners[]={{0,0,0}};
    const aig_event_route routes[]={{runners,1}};
    size_t ids[]={0};
    const aig_trigger triggers[]={{0,ids,1}};
    aig_ter t={&cs,triggers,1,events,routes,1,0};
    const aig_value value={AIG_INT,{.integer=3}};
    assert(aig_validate(&s,&t)==0);
    assert(aig_input_write(&s,0,value)==1);
    assert(aig_input_write(&s,1,value)==-1);
    assert(!aig_input_key("#I:") && !aig_input_key("#") && !aig_input_key(0));
    ids[0]=1; assert(aig_validate(&s,&t)==-4); ids[0]=0;
    slots[1].key=slots[0].key; assert(aig_validate(&s,&t)==-2);
    return 0;
}
