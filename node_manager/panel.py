"""First standalone terminal surface. No implicit flash, reset or network scan."""
import json
import pathlib
from .manager import Manager
from .discovery import serial_ports

def show(value):
    print(json.dumps(value,indent=2,ensure_ascii=False))

def run(manager):
    while True:
        print("\nAIGMos Panel / Node Manager")
        print("1 Nodes  2 USB inventory  3 Register node  4 Network")
        print("5 Configure / import  6 Selected composition  7 Prepare build")
        print("8 Module registry  9 Board registry  0 Exit")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1": show(manager.nodes())
            elif action=="2": show(serial_ports())
            elif action=="3": show(manager.register(input("MAC: "),input("Platform: "),input("Board path: ")))
            elif action=="4":
                mac=input("MAC: ");mode=input("Mode (auto/static/dhcp): ")
                show(manager.network(mac,mode,input("IPv4: ") if mode=="static" else None))
            elif action=="5":
                mac=input("MAC: ");definition=json.loads(pathlib.Path(input("Composition JSON: ")).read_text())
                show(manager.configure(mac,definition))
            elif action=="6": show(manager.selected(input("MAC: ")))
            elif action=="7": show(manager.prepare(input("MAC: "),input("Output directory: ")))
            elif action in ("8","9"):
                from .composition import load
                show(load("embedded/modules/registry.json" if action=="8" else "embedded/adapters/registry.json"))
            else: print("Unknown action")
        except (EOFError,KeyboardInterrupt): return
        except (ValueError,KeyError,OSError,TypeError) as exc: print("ERROR:",exc)

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--registry",default=str(pathlib.Path.home()/".config/aigmos-embed/nodes.json"))
    a=p.parse_args()
    run(Manager(a.registry))

if __name__=="__main__":
    main()
