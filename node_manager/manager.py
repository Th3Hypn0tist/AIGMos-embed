"""Generic Node Manager service; UI and deployment are separate adapters."""
import pathlib
from .registry import Registry, mac_id
from .composition import load, resolve
from .build import prepare

class Manager:
    def __init__(self, path):
        self.registry=Registry(path)

    def nodes(self):
        return sorted(self.registry.data["nodes"].values(),key=lambda n:n["index"])

    def register(self,mac,platform,board):
        if board not in load("embedded/adapters/registry.json")["platforms"][platform]["boards"]:
            raise ValueError("board not registered for platform")
        node=self.registry.register(mac,platform,board)
        self.registry.save()
        return node

    def register_identified(self,identity,board):
        from .registry import mac_id
        if type(identity["flash_bytes"]) is not int or identity["flash_bytes"]<=0:
            raise ValueError("invalid flash capacity")
        mac=mac_id(identity["mac"])
        platform=identity["platform"]
        if board not in load("embedded/adapters/registry.json")["platforms"][platform]["boards"]:
            raise ValueError("board not registered for platform")
        node=self.registry.register(mac,platform,board)
        node["hardware"]={"flash_bytes":identity["flash_bytes"],"last_port":identity["port"]}
        self.registry.save()
        return node

    def prepare_probe(self,mac,output):
        from .probe import prepare
        node=self.registry.data["nodes"][mac_id(mac)]
        return prepare(node["platform"],node["board"],output)

    def import_probe(self,mac,observations):
        from .probe import plan,interpret
        node=self.registry.data["nodes"][mac_id(mac)]
        if mac_id(observations["mac"])!=node["id"]:
            raise ValueError("probe identity mismatch")
        inventory=interpret(plan(node["platform"],node["board"]),observations)
        node["inventory"]=inventory
        self.registry.save()
        return inventory

    def hardware_definition(self,mac):
        from .hardware import blank
        node=self.registry.data["nodes"][mac_id(mac)]
        return self.selected(mac) if node.get("selected") else blank(node)

    def hardware_edit(self,mac,action,**fields):
        from .hardware import edit
        definition=edit(self.hardware_definition(mac),action,**fields)
        return self.configure(mac,definition)

    def hardware_view(self,mac):
        from .hardware import pinout,inventory_candidates
        node=self.registry.data["nodes"][mac_id(mac)]
        d=self.hardware_definition(mac)
        return {"modules":d["modules"],"buses":d["buses"],"pins":pinout(d),
                "candidates":inventory_candidates(node)}

    def network(self,mac,mode,address=None):
        result=self.registry.network(mac,mode,address)
        self.registry.save()
        return result

    def configure(self,mac,definition):
        node=self.registry.data["nodes"][mac_id(mac)]
        if (node["platform"],node["board"])!=(definition["platform"],definition["board"]):
            raise ValueError("composition does not match node")
        manifest=resolve(definition)
        digest=self.registry.store_composition(mac,definition)
        node["selected"]=digest
        self.registry.save()
        return manifest

    def selected(self,mac):
        node=self.registry.data["nodes"][mac_id(mac)]
        if not node.get("selected"):
            raise ValueError("no selected composition")
        return self.registry.restore(mac,node["selected"])

    def select(self,mac,digest):
        self.configure(mac,self.registry.restore(mac,digest))

    def prepare(self,mac,output):
        return prepare(self.selected(mac),pathlib.Path(output))
