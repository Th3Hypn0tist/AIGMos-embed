"""Host-side build planning. Never flash or invoke a target SDK implicitly."""
import hashlib
import json
import pathlib
import subprocess
from .composition import ROOT, resolve
from .generator import generate

def plan(definition):
    manifest=resolve(definition)
    runtime=json.loads((ROOT/"embedded/structure.json").read_text())
    sources=[]
    for feature in manifest["features"]:
        source=runtime["runtime"]["hardcore"]["path"]+"/"+feature+".c"
        if not (ROOT/source).is_file():
            raise ValueError("missing runtime source: "+source)
        sources.append(source)
    core=definition.get("core_features",[])
    if len(set(core))!=len(core) or not set(core)<=set(runtime["runtime"]["core"]["features"]):
        raise ValueError("invalid Core features")
    if "validate" in core and not {"state","cs","ter"}<=set(manifest["features"]):
        raise ValueError("validate requires State, CS, TER")
    for feature in core:
        source=runtime["runtime"]["core"]["path"]+"/"+feature+".c"
        if not (ROOT/source).is_file():
            raise ValueError("missing Core source: "+source)
        sources.append(source)
    modules=json.loads((ROOT/"embedded/modules/registry.json").read_text())["modules"]
    module_sources=sorted({p for instance in manifest["modules"] for p in modules[instance["module"]].get("sources",[])})
    module_headers=sorted({p for instance in manifest["modules"] for p in modules[instance["module"]].get("headers",[])})
    for source in module_sources+module_headers:
        if not (ROOT/source).is_file(): raise ValueError("missing module file: "+source)
    code=generate(definition)
    hashes={source:hashlib.sha256((ROOT/source).read_bytes()).hexdigest() for source in sources+module_sources}
    headers={}
    for folder in ("embedded/hardcore","embedded/core"):
        for header in sorted((ROOT/folder).glob("*.h")):
            headers[str(header.relative_to(ROOT))]=hashlib.sha256(header.read_bytes()).hexdigest()
    for header in module_headers+["embedded/adapters/platform.h"]:
        headers[header]=hashlib.sha256((ROOT/header).read_bytes()).hexdigest()
    result=dict(manifest,core_features=core,runtime_sources=sources,module_sources=module_sources,
                source_hashes=hashes,header_hashes=headers,
                generated_sha256=hashlib.sha256(code.encode()).hexdigest(),
                build_ready=False,missing=["platform adapter","module implementations","target entry point","target toolchain integration"])
    raw=json.dumps(result,sort_keys=True,separators=(",",":"),allow_nan=False)
    result["build_plan_sha256"]=hashlib.sha256(raw.encode()).hexdigest()
    return result,code

def prepare(definition,output):
    manifest,code=plan(definition)
    output=pathlib.Path(output)
    output.mkdir(parents=True,exist_ok=True)
    (output/"composition.c").write_text(code)
    (output/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n")
    return manifest

def compile_objects(definition,output,cc="cc"):
    """Compile selected runtime and generated tables only; no link or flash."""
    output=pathlib.Path(output).resolve()
    manifest=prepare(definition,output)
    log=[]
    sources=[ROOT/p for p in manifest["runtime_sources"]+manifest["module_sources"]]+[output/"composition.c"]
    for index,source in enumerate(sources):
        target=output/f"{index}_{source.stem}.o"
        args=[cc,"-std=c99","-Os","-Wall","-Wextra","-Werror","-pedantic",
              "-ffunction-sections","-fdata-sections","-I",str(ROOT/"embedded"),
              *["-D"+flag for flag in manifest["flags"]],"-c",str(source),"-o",str(target)]
        try:
            run=subprocess.run(args,capture_output=True,text=True,check=False)
            log.append({"argv":args,"returncode":run.returncode,"stdout":run.stdout,"stderr":run.stderr})
            if run.returncode:
                raise RuntimeError("compilation failed: "+str(source))
        except OSError as exc:
            log.append({"argv":args,"error":str(exc)})
            raise
        finally:
            (output/"build-log.json").write_text(json.dumps(log,indent=2)+"\n")
    return manifest

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("definition",type=pathlib.Path)
    p.add_argument("output",type=pathlib.Path)
    p.add_argument("--compile-objects",action="store_true")
    p.add_argument("--cc",default="cc")
    a=p.parse_args()
    definition=json.loads(a.definition.read_text())
    result=compile_objects(definition,a.output,a.cc) if a.compile_objects else prepare(definition,a.output)
    print(result["build_plan_sha256"])

if __name__=="__main__":
    main()
