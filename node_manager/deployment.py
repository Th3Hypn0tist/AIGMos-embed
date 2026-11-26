"""Deployment preparation and inspection. No target writer is available yet."""
import json
from pathlib import Path
from .build import plan,prepare,compile_objects

def inspect(definition,output):
    directory=Path(output)
    current,_=plan(definition)
    manifest_path=directory/"manifest.json"
    if not manifest_path.is_file():
        return {"stage":"unprepared","push_allowed":False,"missing":current["missing"]}
    saved=json.loads(manifest_path.read_text())
    matches=saved.get("build_plan_sha256")==current["build_plan_sha256"]
    log_path=directory/"build-log.json"
    log=json.loads(log_path.read_text()) if log_path.is_file() else []
    count=len(current["runtime_sources"])+len(current["module_sources"])+1
    objects_ok=matches and len(log)==count and all(row.get("returncode")==0 for row in log)
    return {"stage":"stale" if not matches else "host_objects_logged" if objects_ok else "prepared",
            "build_plan_sha256":current["build_plan_sha256"],"missing":current["missing"],
            "push_allowed":False,"reason":"No target link/firmware verification adapter"}

def push(definition,output):
    status=inspect(definition,output)
    raise ValueError("Push blocked: "+status.get("reason","prepare target build first"))
