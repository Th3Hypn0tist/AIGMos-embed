"""Local Arduino toolchain provisioning. Downloads occur only on explicit install."""
import hashlib
import json
import os
import pathlib
import platform
import subprocess
from .composition import ROOT

HOME=ROOT/"toolchains"

def manifest(home=HOME):
    return json.loads((pathlib.Path(home)/"manifest.json").read_text())

def config(home=HOME):
    home=pathlib.Path(home).resolve()
    return {"board_manager":{"additional_urls":[c["index"] for c in manifest(home)["cores"]]},
            "directories":{"data":str(home/"data"),"downloads":str(home/"downloads"),
                           "user":str(home/"user")},
            "library":{"enable_unsafe_install":False},
            "updater":{"enable_notification":False},"metrics":{"enabled":False}}

def configure(home=HOME):
    home=pathlib.Path(home).resolve()
    cfg=config(home)
    for path in cfg["directories"].values(): pathlib.Path(path).mkdir(parents=True,exist_ok=True)
    path=home/"config.json"
    path.write_text(json.dumps(cfg,indent=2)+"\n")
    return path

def cli(home=HOME):
    home=pathlib.Path(home).resolve()
    path=home/manifest(home)["arduino_cli"]["path"]
    if not path.is_file() or not os.access(path,os.X_OK):
        raise ValueError("Local Arduino CLI missing; install the locked binary first")
    return path

def invoke(args,home=HOME,runner=subprocess.run,timeout=1800):
    path=cli(home)
    cfg=configure(home)
    env={k:v for k,v in os.environ.items() if not k.startswith("ARDUINO_")}
    result=runner([str(path),"--config-file",str(cfg),*args],env=env,
                  capture_output=True,text=True,timeout=timeout,check=False)
    if result.returncode: raise RuntimeError("Arduino CLI failed: "+result.stderr[-2000:])
    return result.stdout

def status(home=HOME,runner=subprocess.run):
    spec=manifest(home)
    version=invoke(["version","--format","json"],home,runner,timeout=30)
    info=json.loads(version)
    actual=info.get("VersionString",info.get("version",""))
    if actual!=spec["arduino_cli"]["version"]:
        raise ValueError("Arduino CLI version mismatch: "+str(actual))
    raw=json.loads(invoke(["core","list","--format","json"],home,runner,timeout=30))
    installed={p["id"]:p["installed_version"] for p in raw.get("platforms",[])}
    cores=[dict(c,installed=installed.get(c["id"]),matches=installed.get(c["id"])==c["version"]) for c in spec["cores"]]
    return {"cli":actual,"cores":cores,"versions_match":all(c["matches"] for c in cores)}

def install(home=HOME,runner=subprocess.run):
    if platform.system()!="Linux" or platform.machine() not in ("x86_64","AMD64"):
        raise ValueError("initial package supports Linux x86_64 only")
    status(home,runner) # checks CLI version before network operations
    invoke(["core","update-index"],home,runner)
    for core in manifest(home)["cores"]:
        invoke(["core","install",core["id"]+"@"+core["version"]],home,runner)
    return status(home,runner)

def inventory(home=HOME):
    """Hash installed files for later package verification; not a trust anchor."""
    home=pathlib.Path(home).resolve()
    rows={}
    for folder in ("bin","data","user","sources","licenses"):
        for path in sorted((home/folder).rglob("*")):
            if path.is_symlink(): raise ValueError("symlink requires explicit packaging policy: "+str(path))
            if path.is_file():
                digest=hashlib.sha256()
                with path.open("rb") as stream:
                    for chunk in iter(lambda:stream.read(1024*1024),b""): digest.update(chunk)
                rows[str(path.relative_to(home))]=digest.hexdigest()
    return {"version":1,"files":rows}

def main():
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("action",choices=("status","install","inventory"))
    args=parser.parse_args()
    result={"status":status,"install":install,"inventory":inventory}[args.action]()
    if args.action=="inventory": (HOME/"inventory.json").write_text(json.dumps(result,indent=2)+"\n")
    else: print(json.dumps(result,indent=2))

if __name__=="__main__": main()
