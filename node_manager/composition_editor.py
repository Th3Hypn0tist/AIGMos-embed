"""Draft editor. Structural validation is distinct from native build validation."""
from copy import deepcopy
import json
import re
from .composition import load, resolve

def validate_draft(d):
    manifest=resolve(d)
    runtime=load("embedded/structure.json")
    core=d.get("core_features",[])
    if not isinstance(core,list) or len(set(core))!=len(core) or not set(core)<=set(runtime["runtime"]["core"]["features"]):
        raise ValueError("invalid Core features")
    if "validate" in core and not {"state","cs","ter"}<=set(manifest["features"]):
        raise ValueError("validate requires State, CS, TER")
    variables=d.get("variables",{})
    if not isinstance(variables,dict): raise ValueError("variables must be an object")
    for name in variables:
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name): raise ValueError("invalid variable name")
    json.dumps(variables,allow_nan=False)
    for field in ("ter","pending_ter"):
        regs=d.get(field,{})
        if not isinstance(regs,dict) or set(regs)-{"triggers","events","runners"}:
            raise ValueError("invalid TER registries")
        for kind,entries in regs.items():
            if not isinstance(entries,dict): raise ValueError("registry must be an object")
            for name,entry in entries.items():
                if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",name) or not isinstance(entry,dict):
                    raise ValueError("invalid registry entry")
                if kind=="triggers":
                    condition=entry.get("condition")
                    if field=="pending_ter" and isinstance(condition,dict):
                        if set(condition)!={"interval_ms"} or type(condition["interval_ms"]) is not int or condition["interval_ms"]<=0:
                            raise ValueError("invalid interval condition")
                    elif not isinstance(condition,str) or not condition:
                        raise ValueError("invalid condition")
                if kind in ("triggers","runners"):
                    state=entry.get("state",0)
                    if type(state) is not int or state not in (0,1): raise ValueError("invalid state")
                if kind=="events" and entry.get("trigger") not in regs.get("triggers",{}):
                    raise ValueError("unknown trigger")
                if kind!="triggers":
                    commands=entry.get("commands")
                    if not isinstance(commands,list): raise ValueError("commands must be ordered list")
                    for cmd in commands:
                        if isinstance(cmd,str) and cmd.strip(): continue
                        if isinstance(cmd,dict) and isinstance(cmd.get("command"),str) and isinstance(cmd.get("args",[]),list): continue
                        raise ValueError("invalid command entry")
    return manifest

def edit(definition,section,value):
    allowed={"features","core_features","flags","variables","application_commands","commands","ter","pending_ter"}
    if section not in allowed: raise ValueError("unsupported composition section")
    d=deepcopy(definition)
    d[section]=deepcopy(value)
    validate_draft(d)
    return d

def view(definition):
    manifest=validate_draft(definition)
    return {"features":manifest["features"],"core_features":manifest["core_features"],
            "flags":manifest["flags"],"variables":manifest["variables"],
            "state_inputs":manifest["inputs"],"module_commands":manifest["commands"],
            "application_commands":manifest["application_commands"],"command_bindings":manifest["command_bindings"],
            "ter":manifest["ter"],"pending_ter":manifest["pending_ter"],
            "build_ready":False,"sha256":manifest["sha256"]}
