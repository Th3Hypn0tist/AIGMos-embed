#include "../hardcore/ter.h"
#include "../hardcore/routine.h"
#include <stdio.h>
int main(void) {
    printf("value=%zu slot=%zu state=%zu cs=%zu command=%zu event=%zu trigger=%zu runner=%zu route=%zu ter=%zu routine=%zu\n",
        sizeof(aig_value),sizeof(aig_slot),sizeof(aig_state),sizeof(aig_cs),sizeof(aig_command),
        sizeof(aig_event),sizeof(aig_trigger),sizeof(aig_runner),sizeof(aig_event_route),sizeof(aig_ter),sizeof(aig_routine));
    return 0;
}
