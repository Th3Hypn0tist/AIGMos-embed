#include "../hardcore/ter.h"
#include <assert.h>
static int run(void *ctx,const aig_value *args,size_t argc) {
    assert(argc==1 && args[0].type==AIG_INT);
    *(int *)ctx+=(int)args[0].as.integer; return 0;
}
int main(void) {
    int total=0; size_t n;
    const aig_value arg={AIG_INT,{.integer=2}};
    const aig_command commands[]={{"um.test.run",run,&total}};
    const aig_cs cs={commands,1};
    const aig_runner runners[]={{0,&arg,1}};
    const aig_event_route routes[]={{runners,1},{runners,1}};
    aig_event events[2]={{0},{0}};
    const size_t ids[]={0,1};
    const aig_trigger triggers[]={{0,ids,2}};
    aig_ter ter={&cs,triggers,1,events,routes,2,0};
    aig_slot slots[]={{"#I:sensor",{AIG_NULL,{0}}}};
    aig_state state={slots,1,aig_ter_on_change,&ter};
    assert(aig_cs_execute(&cs,"missing",0,0)==AIG_CS_UNKNOWN);
    assert(aig_cs_execute(&cs,"um.test.run",&arg,1)==0 && total==2);
    assert(aig_state_set(&state,0,arg)==1);
    assert(events[0].pending==1 && events[1].pending==1);
    assert(aig_ter_step(&ter,&n)==0 && n==2 && total==6);
    assert(aig_state_set(&state,0,arg)==0);
    assert(aig_ter_step(&ter,&n)==0 && n==0);
    assert(aig_ter_raise(&ter,2)==-1);
    return 0;
}
