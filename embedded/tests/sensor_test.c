#include "../modules/bmp180/bmp180.h"
#include "../modules/dht11/dht11.h"
#include <assert.h>
int main(void) {
    aig_bmp180 d={.ac1=408,.ac2=-72,.ac3=-14383,.ac4=32741,.ac5=32757,.ac6=23153,
                  .b1=6190,.b2=4,.mb=-32768,.mc=-8711,.md=2868,.ready=1};
    int32_t t,p;double temp,humidity;uint8_t b[]={55,0,24,0,79};
    assert(aig_bmp180_compensate(&d,27898,23843,&t,&p)==0);
    assert(t==150 && p==69964);
    assert(aig_dht11_decode(b,&temp,&humidity)==0 && temp==24 && humidity==55);
    b[4]=0;assert(aig_dht11_decode(b,&temp,&humidity)<0);
    return 0;
}
