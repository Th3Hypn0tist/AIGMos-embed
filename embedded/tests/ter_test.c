#include "../hardcore/ter.h"
#include <assert.h>
static int run(void *ctx,const aig_value *args,size_t argc) {
    assert(argc==1 && args[0].type==AIG_INT);
    *(int *)ctx+=(int)args[0].as.integer; return 0;
}
static int condition(void *ctx,const aig_state *s) {
    aig_value v; (void)ctx;
    return aig_state_get(s,0,&v)==0 && v.type==AIG_INT && v.as.integer>0;
}
int main(void) {
    int total=0; size_t n;
    const aig_value arg={AIG_INT,{.integer=2}}, zero={AIG_INT,{.integer=0}};
    const aig_command commands[]={{"um.test.run",run,&total}};
    const aig_cs cs={commands,1};
    const aig_ter_command list[]={{0,&arg,1}};
    aig_trigger triggers[]={{condition,0,0}};
    const aig_event events[]={{0,list,1},{0,list,1}};
    aig_runner runners[]={{0,list,1}};
    aig_ter ter={&cs,triggers,1,events,2,runners,1,0};
    aig_slot slots[]={{"#I:sensor",{AIG_NULL,{0}}}};
    aig_state state={slots,1,0,0};
    assert(aig_state_set(&state,0,arg)==1);
    assert(aig_ter_evaluate(&ter,&state)==0 && triggers[0].state==1);
    assert(aig_ter_step(&ter,&n)==0 && n==2 && total==4);
    assert(aig_state_set(&state,0,zero)==1);
    assert(aig_ter_evaluate(&ter,&state)==0 && triggers[0].state==0);
    assert(aig_ter_runner_set(&ter,0,1)==0);
    assert(aig_ter_step(&ter,&n)==0 && n==1 && total==6);
    assert(aig_ter_runner_set(&ter,0,0)==0);
    assert(aig_ter_step(&ter,&n)==0 && n==0);
    return 0;
}
