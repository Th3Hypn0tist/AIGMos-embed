"""Host-side network configuration and passive Linux neighbor inventory."""
import ipaddress
import json
import re
import subprocess
from .registry import mac_id

def host_address(value):
    ip=ipaddress.IPv4Address(value)
    if ip.is_unspecified or ip.is_multicast or ip.is_loopback or int(ip)==0xffffffff:
        raise ValueError("invalid destination")
    return str(ip)

def neighbors(runner=subprocess.run):
    result=runner(["ip","-j","-4","neigh","show"],capture_output=True,text=True,timeout=5,check=True)
    entries=[]
    for row in json.loads(result.stdout):
        if not row.get("lladdr") or not row.get("dst"): continue
        states=row.get("state",[])
        if isinstance(states,str): states=[states]
        if set(states)&{"FAILED","INCOMPLETE"}: continue
        try:
            entries.append({"address":host_address(row["dst"]),"mac":mac_id(row["lladdr"]),
                            "interface":row.get("dev"),"state":states})
        except ValueError: continue
    return entries

def occupied(entries,mac):
    key=mac_id(mac)
    return {row["address"] for row in entries if row["mac"]!=key}

def endpoint(address,port):
    if type(port) is not int or not 1<=port<=65535: raise ValueError("invalid UDP port")
    return {"address":host_address(address),"port":port}

def wifi(ssid,password):
    if not isinstance(ssid,str) or not 1<=len(ssid.encode("utf-8"))<=32 or "\x00" in ssid:
        raise ValueError("invalid SSID")
    if not isinstance(password,str) or "\x00" in password:
        raise ValueError("invalid password")
    n=len(password.encode("utf-8"))
    if n!=0 and not 8<=n<=63 and not re.fullmatch(r"[0-9a-fA-F]{64}",password):
        raise ValueError("expected empty, WPA passphrase or 64 hex digits")
    return {"ssid":ssid,"password":password}

def connectivity(address,runner=subprocess.run):
    ip=host_address(address)
    result=runner(["ping","-n","-c","1","-W","1",ip],capture_output=True,text=True,timeout=3,check=False)
    if result.returncode not in (0,1): raise ValueError("ping failed: "+result.stderr.strip())
    return {"address":ip,"icmp_reply":result.returncode==0,"osc_verified":False}
