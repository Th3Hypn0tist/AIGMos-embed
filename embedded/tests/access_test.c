#include "../hardcore/cs.h"
#include <assert.h>
static int run(void *ctx,const aig_value *args,size_t argc) {
    (void)args; (void)argc; ++*(int *)ctx; return 0;
}
static int allow(void *ctx,const char *name,const aig_value *args,size_t argc) {
    (void)name; (void)args; (void)argc; return *(int *)ctx;
}
int main(void) {
    int calls=0, permission=0;
    const aig_command commands[]={{"um.test.run",run,&calls}};
    aig_cs cs={commands,1,0,0};
    assert(aig_cs_run(&cs,0,0,0)==AIG_CS_DENIED && calls==0);
    cs.authorize=allow; cs.access_context=&permission;
    assert(aig_cs_execute(&cs,"um.test.run",0,0)==AIG_CS_DENIED && calls==0);
    permission=1;
    assert(aig_cs_run(&cs,0,0,0)==0 && calls==1);
    permission=-1;
    assert(aig_cs_run(&cs,0,0,0)==AIG_CS_DENIED && calls==1);
    return 0;
}
