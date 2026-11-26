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

    def network(self,mac,mode,address=None,observations=()):
        from .network import occupied
        result=self.registry.network(mac,mode,address,occupied(observations,mac))
        self.registry.save()
        return result

    def network_view(self,mac,observations=()):
        node=self.registry.data["nodes"][mac_id(mac)]
        return {"network":node["network"],"hardware":node.get("hardware",{}),
                "neighbors":[row for row in observations if row["mac"]==node["id"]],
                "wifi_configured":self._wifi_path(mac).exists()}

    def _wifi_path(self,mac):
        return self.registry.path.parent/"wifi"/(mac_id(mac)+".json")

    def set_wifi(self,mac,ssid,password):
        import json,os,tempfile
        from .network import wifi
        self.registry.data["nodes"][mac_id(mac)]
        data=wifi(ssid,password)
        path=self._wifi_path(mac)
        path.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
        fd,tmp=tempfile.mkstemp(dir=path.parent)
        try:
            with os.fdopen(fd,"w") as stream:
                json.dump(data,stream)
            os.replace(tmp,path)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        return {"ssid":ssid,"configured":True}

    def set_endpoint(self,mac,address,port):
        from .network import endpoint
        dest=endpoint(address,port)
        definition=self.hardware_definition(mac)
        definition.setdefault("variables",{})["master"]=dest["address"]
        definition.setdefault("osc",{})["port"]=dest["port"]
        return self.configure(mac,definition)

    def composition_view(self,mac):
        from .composition_editor import view
        return view(self.hardware_definition(mac))

    def composition_edit(self,mac,section,value):
        from .composition_editor import edit
        return self.configure(mac,edit(self.hardware_definition(mac),section,value))

    def history(self,mac):
        node=self.registry.data["nodes"][mac_id(mac)]
        return [{"sha256":item["sha256"],"selected":item["sha256"]==node.get("selected"),
                 "active":item["sha256"]==node.get("active")} for item in node["compositions"]]

    def configure(self,mac,definition):
        node=self.registry.data["nodes"][mac_id(mac)]
        if (node["platform"],node["board"])!=(definition["platform"],definition["board"]):
            raise ValueError("composition does not match node")
        from .composition_editor import validate_draft
        manifest=validate_draft(definition)
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

    def compile_host(self,mac,output):
        from .build import compile_objects
        return compile_objects(self.selected(mac),output)

    def deployment_status(self,mac,output):
        from .deployment import inspect
        node=self.registry.data["nodes"][mac_id(mac)]
        return dict(inspect(self.selected(mac),output),selected=node.get("selected"),active=node.get("active"))

    def push(self,mac,output):
        from .deployment import push
        return push(self.selected(mac),output)
