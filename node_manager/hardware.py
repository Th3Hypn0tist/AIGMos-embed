"""Generic, transactional hardware composition editing."""
from copy import deepcopy
from .composition import load, resolve
from .pinmap import validate

def blank(node):
    return {"platform":node["platform"],"board":node["board"],
            "buses":{},"modules":[],"features":["state","input","cs","ter"],"flags":[]}

def metadata(definition):
    return (load("embedded/adapters/"+definition["board"]),
            load("embedded/modules/registry.json"))

def pinout(definition):
    board,registry=metadata(definition)
    used=validate(board,registry,definition["buses"],definition["modules"])
    result=[]
    for pin in sorted(set(map(int,board["pins"])) | set(board.get("reserved",[]))):
        meta=board["pins"].get(str(pin),{})
        reserved=pin in board.get("reserved",[])
        strap=str(pin) in board.get("strap",{})
        result.append({"gpio":pin,"label":meta.get("label","-"),
                       "capabilities":meta.get("capabilities",[]),
                       "owner":used.get(pin),"blocked":reserved or strap,
                       "reason":"reserved" if reserved else "boot strap" if strap else None})
    return result

def available(definition,capability):
    return [p for p in pinout(definition) if not p["blocked"] and p["owner"] is None
            and capability in p["capabilities"]]

def edit(definition,action,**fields):
    d=deepcopy(definition)
    modules=d["modules"]
    if action=="bus":
        d["buses"][fields["name"]]={"kind":"i2c","sda":fields["sda"],"scl":fields["scl"]}
    elif action=="remove_bus":
        del d["buses"][fields["name"]]
    elif action=="add":
        modules.append({"id":fields["id"],"module":fields["module"],"bindings":fields["bindings"]})
    elif action in ("remove","replace","bind"):
        index=next((i for i,m in enumerate(modules) if m["id"]==fields["id"]),None)
        if index is None: raise ValueError("unknown module instance")
        if action=="remove": modules.pop(index)
        elif action=="replace":
            modules[index]={"id":fields["id"],"module":fields["module"],"bindings":fields["bindings"]}
        else: modules[index]["bindings"]=fields["bindings"]
    else: raise ValueError("unknown hardware action")
    resolve(d)
    return d

def inventory_candidates(node):
    """Do not auto-select devices or guess GPIO bindings."""
    inv=node.get("inventory",{})
    return deepcopy(inv.get("devices",[]))
