#include "../hardcore/routine.h"
#include <assert.h>
static int record(void *ctx,const aig_value *args,size_t argc) {
    int *n=ctx;
    if (argc!=1 || args[0].type!=AIG_INT) return -9;
    *n=*n*10+(int)args[0].as.integer;
    return 0;
}
static int fail(void *ctx,const aig_value *args,size_t argc) {
    (void)ctx; (void)args; (void)argc; return -7;
}
int main(void) {
    int n=0;
    const aig_value one={AIG_INT,{.integer=1}}, two={AIG_INT,{.integer=2}};
    aig_routine routine={0,0,0,0};
    const aig_command commands[]={{"um.a.closed",record,&n},{"um.b.closed",record,&n},{"&venttiilit.kiinni",aig_routine_call,&routine},{"fail",fail,0}};
    const aig_cs cs={commands,4};
    const aig_routine_step steps[]={{0,&one,1},{1,&two,1}};
    const aig_routine_step broken[]={{0,&one,1},{3,0,0},{1,&two,1}};
    const aig_routine_step recursive[]={{2,0,0}};
    routine.cs=&cs; routine.steps=steps; routine.count=2;
    assert(aig_cs_execute(&cs,"&venttiilit.kiinni",0,0)==0 && n==12);
    n=0; routine.steps=broken; routine.count=3;
    assert(aig_cs_execute(&cs,"&venttiilit.kiinni",0,0)==-7 && n==1 && !routine.running);
    routine.steps=recursive; routine.count=1;
    assert(aig_cs_execute(&cs,"&venttiilit.kiinni",0,0)==AIG_CS_INVALID && !routine.running);
    return 0;
}
