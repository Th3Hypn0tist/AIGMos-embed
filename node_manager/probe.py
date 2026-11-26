"""Generate board-specific probe tables and interpret raw hardware observations."""
import json
from .composition import load

def plan(platform,board_path):
    if board_path not in load("embedded/adapters/registry.json")["platforms"][platform]["boards"]:
        raise ValueError("unregistered board")
    board=load("embedded/adapters/"+board_path)
    safe={int(pin) for pin,meta in board["pins"].items() if meta.get("probe_safe")
          and int(pin) not in board["reserved"] and pin not in board["strap"]}
    bus=board["defaults"]["i2c"]
    if bus["sda"]==bus["scl"] or any(p not in safe or "i2c" not in board["pins"][str(p)]["capabilities"] for p in bus.values()):
        raise ValueError("unsafe default I2C bus")
    checks={}
    for name,spec in load("embedded/modules/registry.json")["modules"].items():
        if spec["interface"]!="i2c": continue
        for addr in spec["bindings"]["address"]:
            probe=spec["probe"]
            checks.setdefault(addr,set())
            if probe is not None: checks[addr].add(probe["register"])
    return {"version":1,"platform":platform,"board":board_path,"bus":bus,
            "gpio":sorted(p for p in safe-set(bus.values()) if "gpio" in board["pins"][str(p)]["capabilities"]),
            "i2c":[{"address":a,"registers":sorted(regs)} for a,regs in sorted(checks.items())]}

def generate(p):
    rows=[(entry["address"],reg) for entry in p["i2c"] for reg in (entry["registers"] or [256])]
    return ('#include "probe.h"\n'
            +f'const unsigned probe_sda={p["bus"]["sda"]}, probe_scl={p["bus"]["scl"]};\n'
            +'const aig_probe_check probe_checks[]={'+','.join('{%d,%d}'%r for r in rows)+'};\n'
            +f'const size_t probe_count={len(rows)};\n'
            +'const unsigned probe_gpio[]={'+','.join(map(str,p["gpio"]))+'};\n'
            +f'const size_t probe_gpio_count={len(p["gpio"])};\n')

def interpret(p,observations):
    if observations.get("version")!=1: raise ValueError("unsupported probe version")
    allowed={(x["address"],r) for x in p["i2c"] for r in (x["registers"] or [256])}
    values={}
    for row in observations["i2c"]:
        key=(row["address"],row["register"])
        value=row["value"]
        if key not in allowed or key in values or (value is not None and (type(value) is not int or not 0<=value<=255)):
            raise ValueError("invalid probe observation")
        values[key]=value
    if set(values)!=allowed: raise ValueError("incomplete I2C observations")
    gpio=observations["gpio"]
    if set(gpio)!=set(map(str,p["gpio"])) or any(type(v) is not int or v not in (0,1) for v in gpio.values()):
        raise ValueError("invalid GPIO observations")
    devices=[]
    for name,spec in load("embedded/modules/registry.json")["modules"].items():
        if spec["interface"]!="i2c": continue
        for addr in spec["bindings"]["address"]:
            probe=spec["probe"]
            if probe and values.get((addr,probe["register"]))==probe["id"]:
                devices.append({"module":name,"address":addr,"status":"id_match"})
            elif probe is None and any(a==addr and v is not None for (a,r),v in values.items()):
                devices.append({"module":name,"address":addr,"status":"candidate"})
    return {"version":1,"bus":p["bus"],"devices":devices,"gpio":gpio,"raw":observations}

def prepare(platform,board,output):
    from pathlib import Path
    p=plan(platform,board)
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    (output/"probe_plan.json").write_text(json.dumps(p,indent=2)+"\n")
    (output/"probe_config.c").write_text(generate(p))
    return p
