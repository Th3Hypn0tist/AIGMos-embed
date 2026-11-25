#pragma once
#include <Arduino.h>
#include <WiFi.h>
#include <mbedtls/md.h>
#include <mbedtls/base64.h>
#include <mbedtls/pkcs5.h>
#include <esp_system.h>

// PostgreSQL v3, SCRAM-SHA-256, extended query protocol. LAN TCP only.
class PgClient {
  WiFiClient c;
  static constexpr uint32_t timeout = 3500;
  static void u32(String &s,uint32_t n){for(int i=3;i>=0;i--)s+=(char)(n>>(8*i));}
  static void u16(String &s,uint16_t n){s+=(char)(n>>8);s+=(char)n;}
  static void z(String &s,const char *p){s+=p;s+=(char)0;}
  static uint32_t get32(const uint8_t *p){return (uint32_t(p[0])<<24)|(uint32_t(p[1])<<16)|(uint32_t(p[2])<<8)|p[3];}
  bool writeAll(const uint8_t *p,size_t n){return c.write(p,n)==n;}
  bool send(char t,const String &s){
    uint8_t h[5];uint32_t n=s.length()+4;
    h[0]=t;for(int i=0;i<4;i++)h[i+1]=n>>(24-i*8);
    return writeAll(h,5)&&writeAll((const uint8_t*)s.c_str(),s.length());
  }
  bool readAll(uint8_t *p,size_t n,uint32_t start){
    while(n){if(millis()-start>timeout)return false;int a=c.available();
      if(a>0){int k=c.read(p,min(n,(size_t)a));if(k<=0)return false;p+=k;n-=k;}
      else {if(!c.connected())return false;delay(1);}}
    return true;
  }
  bool frame(char &t,uint8_t *b,size_t &n,uint32_t start){
    uint8_t h[5];if(!readAll(h,5,start))return false;t=h[0];uint32_t l=get32(h+1);
    if(l<4||l-4>4096)return false;n=l-4;
    if(!readAll(b,n,start))return false;b[n]=0;return true;
  }
  static String b64(const uint8_t *p,size_t n){
    unsigned char b[256];size_t k=0;
    if(mbedtls_base64_encode(b,sizeof(b),&k,p,n))return "";
    b[k]=0;return String((char*)b);
  }
  static bool hmac(const uint8_t *key,size_t n,const String &s,uint8_t *out){
    return !mbedtls_md_hmac(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),key,n,(const uint8_t*)s.c_str(),s.length(),out);
  }
  static String attr(const String &s,char k){
    int i=0;while(i<(int)s.length()){int e=s.indexOf(',',i);if(e<0)e=s.length();
      if(s[i]==k&&s[i+1]=='=')return s.substring(i+2,e);i=e+1;}return "";
  }
public:
  void close(){c.stop();}
  bool connected(){return c.connected();}
  bool login(const char *host,uint16_t port,const char *db,const char *user,const char *password){
    close();if(!c.connect(host,port,1500))return false;
    String s;u32(s,196608);z(s,"user");z(s,user);z(s,"database");z(s,db);z(s,"client_encoding");z(s,"UTF8");s+=(char)0;
    String h;u32(h,s.length()+4);
    if(!writeAll((const uint8_t*)h.c_str(),h.length())||!writeAll((const uint8_t*)s.c_str(),s.length())){close();return false;}
    uint8_t b[4097];size_t n;char t;String nonce,bare,expected;bool auth=false,verified=false;
    uint32_t start=millis();
    while(frame(t,b,n,start)){
      if(t=='E')break;
      if(t=='Z'){if(auth&&verified&&n==1&&b[0]=='I')return true;break;}
      if(t!='R')continue;
      if(n<4)break;uint32_t code=get32(b);
      if(code==0){auth=true;continue;}
      if(code==10){
        bool found=false;for(size_t i=4;i<n&&b[i];){size_t k=strlen((char*)b+i);if(i+k>=n)break;if(!strcmp((char*)b+i,"SCRAM-SHA-256"))found=true;i+=k+1;}
        if(!found)break;
        uint8_t rnd[18];esp_fill_random(rnd,sizeof(rnd));nonce=b64(rnd,sizeof(rnd));
        bare="n=,r="+nonce;String first="n,,"+bare;String p;z(p,"SCRAM-SHA-256");u32(p,first.length());p+=first;
        if(!send('p',p))break;
      }else if(code==11){
        if(bare.isEmpty())break;String sf((char*)b+4);String r=attr(sf,'r'),salt=attr(sf,'s'),iter=attr(sf,'i');
        if(!r.startsWith(nonce)||r.length()<=nonce.length()||salt.isEmpty()||attr(sf,'m').length())break;
        for(size_t j=0;j<iter.length();j++)if(iter[j]<'0'||iter[j]>'9'){iter="";break;}
        long rounds=iter.toInt();if(rounds<4096||rounds>100000)break;
        uint8_t sb[128],sp[32],ck[32],sk[32],sig[32],server[32];size_t sl=0;
        if(mbedtls_base64_decode(sb,sizeof(sb),&sl,(const uint8_t*)salt.c_str(),salt.length()))break;
        mbedtls_md_context_t ctx;mbedtls_md_init(&ctx);
        int rc=mbedtls_md_setup(&ctx,mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),1);
        if(!rc)rc=mbedtls_pkcs5_pbkdf2_hmac(&ctx,(const uint8_t*)password,strlen(password),sb,sl,rounds,32,sp);
        mbedtls_md_free(&ctx);if(rc)break;
        String fin="c=biws,r="+r,am=bare+","+sf+","+fin;
        if(!hmac(sp,32,"Client Key",ck)||mbedtls_md(mbedtls_md_info_from_type(MBEDTLS_MD_SHA256),ck,32,sk)||!hmac(sk,32,am,sig)||!hmac(sp,32,"Server Key",server)||!hmac(server,32,am,sk))break;
        expected=b64(sk,32);for(int j=0;j<32;j++)ck[j]^=sig[j];
        if(!send('p',fin+",p="+b64(ck,32)))break;
      }else if(code==12){
        if(expected.isEmpty()||attr(String((char*)b+4),'v')!=expected)break;verified=true;
      }else break;
    }
    close();return false;
  }
  bool ingest(const String *values,const bool *nulls){
    return execute("SELECT aqm.ingest($1::text,$2::text,$3::text,$4::text,$5::bigint,$6::bigint,$7::real,$8::real,$9::real,$10::real,$11::integer,$12::integer,$13::boolean,$14::smallint,$15::text,$16::text,$17::smallint)",values,nulls,17);
  }
  bool calibration(const String *values,const bool *nulls){
    return execute("SELECT aqm.record_calibration($1::text,$2::text,$3::bigint,$4::real,$5::real,$6::real,$7::real,$8::real)",values,nulls,8);
  }
private:
  bool execute(const char *query,const String *values,const bool *nulls,uint16_t count){
    String p;z(p,"");z(p,query);u16(p,0);
    if(!send('P',p)){close();return false;}
    p="";z(p,"");z(p,"");u16(p,0);u16(p,count);
    for(int i=0;i<count;i++){u32(p,nulls[i]?0xffffffff:values[i].length());if(!nulls[i])p+=values[i];}
    u16(p,0);if(!send('B',p)){close();return false;}
    p="";z(p,"");u32(p,0);if(!send('E',p)||!send('S',"")){close();return false;}
    uint8_t b[4097];size_t n;char t;bool ok=false,err=false;uint32_t start=millis();
    while(frame(t,b,n,start)){
      if(t=='E'){err=true;Serial.printf("PG error: %s\n",n>1?(char*)b+1:"");}
      if(t=='C')ok=true;
      if(t=='Z'){if(!err&&ok&&n==1&&b[0]=='I')return true;break;}
    }
    close();return false;
  }
};
