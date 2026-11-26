"""Explicit build actions; no automatic compilation or flash."""
from pathlib import Path
import json

def run(manager,mac,show):
    output=input("Build directory: ").strip()
    if not output: raise ValueError("build directory required")
    while True:
        print("\nBuild / Deployment Manager")
        show(manager.deployment_status(mac,output))
        print("1 Prepare plan  2 Compile host objects  3 Build log  4 Push to node  0 Back")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1": show(manager.prepare(mac,output))
            elif action=="2": show(manager.compile_host(mac,output))
            elif action=="3":
                path=Path(output)/"build-log.json"
                show(json.loads(path.read_text()) if path.is_file() else [])
            elif action=="4": manager.push(mac,output)
            else: print("Unknown action")
        except (ValueError,KeyError,OSError,RuntimeError,TypeError) as exc: print("ERROR:",exc)
