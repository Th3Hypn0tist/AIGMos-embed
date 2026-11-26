"""First standalone terminal surface. No implicit flash, reset or network scan."""
import json
import pathlib
from .manager import Manager
from .discovery import serial_ports
from .identify import identify, toolchain

def show(value):
    print(json.dumps(value,indent=2,ensure_ascii=False))

def run(manager):
    while True:
        print("\nAIGMos Panel / Node Manager")
        print("1 Nodes  2 USB inventory  3 Register node  4 Network")
        print("5 Configure / import  6 Selected composition  7 Prepare build")
        print("8 Module registry  9 Board registry  10 Identify MCU  11 Toolchain  0 Exit")
        print("12 Prepare probe  13 Import probe observations  14 Hardware / Pin Mapper  15 Composition Manager")
        print("16 Build / Deployment Manager  17 Build probe firmware")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1": show(manager.nodes())
            elif action=="2": show(serial_ports())
            elif action=="3": show(manager.register(input("MAC: "),input("Platform: "),input("Board path: ")))
            elif action=="4":
                from .network_panel import run as network_run
                network_run(manager,input("MAC: "),show)
            elif action=="5":
                mac=input("MAC: ");definition=json.loads(pathlib.Path(input("Composition JSON: ")).read_text())
                show(manager.configure(mac,definition))
            elif action=="6": show(manager.selected(input("MAC: ")))
            elif action=="7": show(manager.prepare(input("MAC: "),input("Output directory: ")))
            elif action=="10":
                ports=serial_ports()
                for i,port in enumerate(ports,1): print(i,port["port"],port["usb"])
                if not ports: print("No serial devices"); continue
                index=int(input("Device number: "))
                if not 1<=index<=len(ports): raise ValueError("invalid device selection")
                if input("Identify may reset the selected device. Type IDENTIFY: ")!="IDENTIFY": continue
                identity=identify(ports[index-1]["port"])
                show(identity)
                from .composition import load
                boards=load("embedded/adapters/registry.json")["platforms"][identity["platform"]]["boards"]
                for i,board in enumerate(boards,1): print(i,board)
                if not boards: print("No supported board metadata"); continue
                selection=input("Board number (blank to skip registration): ").strip()
                if selection:
                    index=int(selection)
                    if not 1<=index<=len(boards): raise ValueError("invalid board selection")
                    show(manager.register_identified(identity,boards[index-1]))
            elif action=="11": show(toolchain())
            elif action=="12": show(manager.prepare_probe(input("MAC: "),input("Output directory: ")))
            elif action=="13":
                mac=input("MAC: ");data=json.loads(pathlib.Path(input("Probe JSON: ")).read_text())
                show(manager.import_probe(mac,data))
            elif action=="14":
                from .hardware_panel import run as hardware_run
                hardware_run(manager,input("MAC: "),show)
            elif action=="15":
                from .composition_panel import run as composition_run
                composition_run(manager,input("MAC: "),show)
            elif action=="16":
                from .deployment_panel import run as deployment_run
                deployment_run(manager,input("MAC: "),show)
            elif action=="17":
                show(manager.build_probe(input("MAC: "),input("New build directory: ")))
            elif action in ("8","9"):
                from .composition import load
                show(load("embedded/modules/registry.json" if action=="8" else "embedded/adapters/registry.json"))
            else: print("Unknown action")
        except (EOFError,KeyboardInterrupt): return
        except (ValueError,KeyError,OSError,TypeError,RuntimeError) as exc: print("ERROR:",exc)

def main():
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--registry",default=str(pathlib.Path.home()/".config/aigmos-embed/nodes.json"))
    a=p.parse_args()
    run(Manager(a.registry))

if __name__=="__main__":
    main()
