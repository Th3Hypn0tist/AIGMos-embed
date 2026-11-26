"""Generate native tables from a resolved composition. No target SDK required."""
import json
import pathlib
import re
from .composition import resolve

def identifier(value):
    if not isinstance(value,str) or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",value):
        raise ValueError("invalid C identifier")
    return value

def literal(value):
    if not isinstance(value,str) or not value.isascii() or any(ord(c)<32 for c in value):
        raise ValueError("invalid table string")
    return json.dumps(value)

def generate(definition):
    m=resolve(definition)
    if not {"state","cs","ter"} <= set(m["features"]):
        raise ValueError("table generator currently requires state, cs, ter")
    if m["flags"]:
        raise ValueError("authorization binding not yet supported by generator")
    regs=definition.get("ter",{})
    if set(regs)-{"triggers","events","runners"}:
        raise ValueError("unknown TER registry")
    triggers=regs.get("triggers",{})
    events=regs.get("events",{})
    runners=regs.get("runners",{})
    commands=definition.get("commands",{})
    if set(commands) != {x["name"] for x in m["commands"]} | set(definition.get("application_commands",[])):
        raise ValueError("explicit command handler bindings must match declared commands")
    for registry in (triggers,events,runners):
        for key in registry:
            identifier(key)
    lines=['#include "hardcore/ter.h"','']
    def add(s): lines.append(s)
    def array(ctype,name,rows,constant=False):
        if not rows: return "0"
        add("static "+("const " if constant else "")+ctype+" "+name+"[]={")
        for row in rows: add("    "+row+",")
        add("};")
        return name
    bindings={}
    for name,handler in commands.items():
        literal(name)
        handler=identifier(handler)
        bindings[name]=handler
    for handler in sorted(set(bindings.values())):
        add(f"extern int {handler}(void *,const aig_value *,size_t);")
    for handler in sorted({identifier(t["condition"]) for t in triggers.values()}):
        add(f"extern int {handler}(void *,const aig_state *);")
    slots=array("aig_slot","slots",["{"+literal(x["key"])+",{AIG_NULL,{0}}}" for x in m["inputs"]])
    add(f"aig_state generated_state={{{slots},{len(m['inputs'])},0,0}};")
    table=array("aig_command","commands",["{"+literal(name)+","+handler+",0}" for name,handler in bindings.items()],True)
    add(f"const aig_cs generated_cs={{{table},{len(bindings)}}};")
    trig=array("aig_trigger","triggers",["{"+identifier(t["condition"])+",0,0}" for t in triggers.values()])
    indices={name:i for i,name in enumerate(bindings)}
    trigger_indices={name:i for i,name in enumerate(triggers)}
    def command_list(prefix, key, entry):
        rows=[]
        for name in entry["commands"]:
            if name not in indices: raise ValueError("unknown command: "+name)
            rows.append("{"+str(indices[name])+",0,0}")
        return array("aig_ter_command",prefix+"_"+key,rows,True),len(rows)
    event_rows=[]
    for key,e in events.items():
        if e["trigger"] not in trigger_indices: raise ValueError("unknown trigger")
        ptr,n=command_list("event",key,e)
        event_rows.append(f"{{{trigger_indices[e['trigger']]},{ptr},{n}}}")
    runner_rows=[]
    for key,r in runners.items():
        state=r.get("state",0)
        if type(state) is not int or state not in (0,1): raise ValueError("invalid runner state")
        ptr,n=command_list("runner",key,r)
        runner_rows.append(f"{{{state},{ptr},{n}}}")
    ep=array("aig_event","events",event_rows,True)
    rp=array("aig_runner","runners",runner_rows)
    add(f"aig_ter generated_ter={{&generated_cs,{trig},{len(triggers)},{ep},{len(events)},{rp},{len(runners)},0}};")
    return "\n".join(lines)+"\n"

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("definition",type=pathlib.Path)
    parser.add_argument("output",type=pathlib.Path)
    args=parser.parse_args()
    args.output.write_text(generate(json.loads(args.definition.read_text())))

if __name__=="__main__":
    main()
