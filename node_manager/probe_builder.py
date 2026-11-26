"""Stage and compile a standalone ESP8266 probe; never upload."""
import hashlib
import json
from pathlib import Path
import shutil
from .composition import ROOT,load
from .probe import plan,generate,interpret
from . import toolchains

def stage(platform,board,output):
    if platform!="ESP8266": raise ValueError("probe backend unavailable")
    p=plan(platform,board)
    meta=load("embedded/adapters/"+board)
    fqbn=meta["arduino_fqbn"]
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=True)
    sketch=output/"aig_probe"
    sketch.mkdir() # require a fresh staging directory
    sources={
        "esp8266/probe_entry.ino":"aig_probe.ino",
        "platform.h":"src/platform.h",
        "esp8266/adapter.h":"src/esp8266/adapter.h",
        "esp8266/adapter.cpp":"src/esp8266/adapter.cpp",
        "probe/probe.h":"src/probe/probe.h",
        "probe/probe.c":"src/probe/probe.c"}
    for src,dst in sources.items():
        target=sketch/dst
        target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/"embedded/adapters"/src,target)
    (sketch/"src/probe/probe_config.c").write_text(generate(p))
    hashes={str(f.relative_to(sketch)):hashlib.sha256(f.read_bytes()).hexdigest()
            for f in sorted(sketch.rglob("*")) if f.is_file()}
    result={"version":1,"kind":"hardware_probe","fqbn":fqbn,"plan":p,
            "source_hashes":hashes,"build_ready":False}
    (output/"probe_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def build(platform,board,output,home=toolchains.HOME):
    output=Path(output).resolve()
    versions=toolchains.status(home)
    core=next((c for c in versions["cores"] if c["id"]=="esp8266:esp8266"),None)
    if not core or not core["matches"]: raise ValueError("locked ESP8266 core not installed")
    result=stage(platform,board,output)
    artifacts=output/"artifacts"
    artifacts.mkdir()
    try:
        log=toolchains.invoke(["compile","--fqbn",result["fqbn"],"--output-dir",str(artifacts),
                               str(output/"aig_probe")],home)
    except (RuntimeError,OSError) as exc:
        (output/"probe-build.log").write_text(str(exc))
        raise
    (output/"probe-build.log").write_text(log)
    binary=artifacts/"aig_probe.ino.bin"
    if not binary.is_file() or not binary.stat().st_size:
        raise ValueError("probe binary missing")
    result.update(build_ready=True,toolchain=versions,
                  artifact=str(binary.relative_to(output)),
                  artifact_sha256=hashlib.sha256(binary.read_bytes()).hexdigest())
    (output/"probe_manifest.json").write_text(json.dumps(result,indent=2)+"\n")
    return result

def parse_report(line,probe_plan):
    if not line.startswith("AIGPROBE "): raise ValueError("not a probe report")
    data=json.loads(line[len("AIGPROBE "):])
    from .registry import mac_id
    mac_id(data["mac"])
    interpret(probe_plan,data)
    return data
