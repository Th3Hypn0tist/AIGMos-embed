#pragma once
#include <WiFiUdp.h>
#include <vector>
using Bytes=std::vector<uint8_t>;
WiFiUDP udp;
void oscU32(Bytes& b,uint32_t v){for(int i=3;i>=0;--i)b.push_back(v>>(i*8));}
void oscU64(Bytes& b,uint64_t v){oscU32(b,v>>32);oscU32(b,v);}
void oscString(Bytes& b,const char* s){while(*s)b.push_back(*s++);b.push_back(0);while(b.size()%4)b.push_back(0);}
void oscFloat(Bytes& b,float f){uint32_t v;memcpy(&v,&f,4);oscU32(b,v);}
struct OscMessage{
  String tags=",";
  Bytes payload;
  void s(const char* v){tags+="s";oscString(payload,v);}
  void i(int32_t v){tags+="i";oscU32(payload,v);}
  void h(uint64_t v){tags+="h";oscU64(payload,v);}
  void f(float v){if(!isfinite(v)){tags+="N";return;}tags+="f";oscFloat(payload,v);}
  void optionalInt(int v){if(v<0)tags+="N";else i(v);}
  void boolean(bool v){tags+=v?'T':'F';}
  bool send(const char* address){
    Bytes msg,packet;oscString(msg,address);oscString(msg,tags.c_str());
    msg.insert(msg.end(),payload.begin(),payload.end());
    oscString(packet,"#bundle");oscU64(packet,1);oscU32(packet,msg.size());
    packet.insert(packet.end(),msg.begin(),msg.end());
    if(!udp.beginPacket(OSC_HOST,OSC_PORT))return false;
    return udp.write(packet.data(),packet.size())==packet.size()&&udp.endPacket()==1;
  }
};
