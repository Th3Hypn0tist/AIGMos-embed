"""Temporary terminal editor; no hardware writes."""
from .composition import load
from .hardware import available

def show_pins(pins):
    print("GPIO  LABEL  CAPABILITIES  ASSIGNMENT")
    for p in pins:
        print(f'{p["gpio"]:>4}  {p["label"]:<5}  {",".join(p["capabilities"]):<14} {p["reason"] or p["owner"] or "free"}')

def run(manager,mac,show):
    while True:
        view=manager.hardware_view(mac)
        print("\nHardware / Modules / Pin Mapper")
        show({"buses":view["buses"],"modules":view["modules"],"candidates":view["candidates"]})
        show_pins(view["pins"])
        print("1 Set I2C bus  2 Add module  3 Remove module  4 Replace module")
        print("5 Rebind module  6 Remove bus  7 Available pins  0 Back")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1":
                manager.hardware_edit(mac,"bus",name=input("Bus name: "),sda=int(input("SDA GPIO: ")),scl=int(input("SCL GPIO: ")))
            elif action=="6": manager.hardware_edit(mac,"remove_bus",name=input("Bus name: "))
            elif action=="3": manager.hardware_edit(mac,"remove",id=input("Instance ID: "))
            elif action=="7": show(available(manager.hardware_definition(mac),input("Capability: ")))
            elif action in ("2","4","5"):
                registry=load("embedded/modules/registry.json")["modules"]
                ident=input("Instance ID: ")
                if action=="5":
                    module=next((m["module"] for m in view["modules"] if m["id"]==ident),None)
                    if module is None: raise ValueError("unknown module instance")
                else:
                    show({name:{"interface":spec["interface"],"bindings":spec["bindings"],"status":spec["status"]} for name,spec in registry.items()})
                    module=input("Module type: ")
                spec=registry[module]
                if spec["interface"]=="i2c":
                    bindings={"bus":input("Bus: "),"address":int(input("Address (0x.. or decimal): "),0)}
                elif spec["interface"]=="gpio": bindings={"data":int(input("Data GPIO: "))}
                else: raise ValueError("unsupported interface")
                if action=="5": manager.hardware_edit(mac,"bind",id=ident,bindings=bindings)
                else: manager.hardware_edit(mac,"add" if action=="2" else "replace",id=ident,module=module,bindings=bindings)
            else: print("Unknown action")
        except (ValueError,KeyError,TypeError) as exc: print("ERROR:",exc)
