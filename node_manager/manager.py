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
