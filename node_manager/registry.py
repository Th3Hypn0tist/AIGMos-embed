"""Single-writer local node registry. Never commit credentials."""
import ipaddress
import json
import os
import pathlib
import re
import tempfile

def mac_id(mac):
    if not isinstance(mac, str) or not re.fullmatch(r"(?:[0-9a-fA-F]{12}|[0-9a-fA-F]{2}(?::[0-9a-fA-F]{2}){5}|[0-9a-fA-F]{2}(?:-[0-9a-fA-F]{2}){5})", mac):
        raise ValueError("invalid MAC")
    return mac.replace(":", "").replace("-", "").lower()

class Registry:
    def __init__(self, path):
        self.path = pathlib.Path(path)
        self.data = json.loads(self.path.read_text()) if self.path.exists() else {"version": 1, "nodes": {}}
        if self.data["version"] != 1:
            raise ValueError("unsupported registry version")

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, name = tempfile.mkstemp(dir=self.path.parent)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(self.data, stream, indent=2, sort_keys=True, allow_nan=False)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def register(self, mac, platform, board):
        key = mac_id(mac)
        nodes = self.data["nodes"]
        if key in nodes:
            node = nodes[key]
            if (node["platform"], node["board"]) != (platform, board):
                raise ValueError("identity already bound to another platform/board")
            return node
        index = max((n["index"] for n in nodes.values()), default=0) + 1
        if platform=="ESP32-C6" and not any(n["index"]==0 for n in nodes.values()):
            index=0
        node = {"id": key, "index": index, "platform": platform, "board": board,
                "network": {"mode": "dhcp"}, "compositions": [], "active": None}
        nodes[key] = node
        return node

    def network(self, mac, mode, address=None, occupied=()):
        node = self.data["nodes"][mac_id(mac)]
        others = {n["network"].get("address") for n in self.data["nodes"].values() if n is not node}
        others.update(str(ipaddress.IPv4Address(a)) for a in occupied)
        # Existing production C6 reservation is released only to its registered owner.
        if node["platform"] != "ESP32-C6" or node["index"] != 0:
            others.add("192.168.0.50")
        others.add("192.168.0.18")
        if mode == "dhcp":
            if address is not None:
                raise ValueError("DHCP cannot have a static address")
            # Keep the old reservation even while DHCP is selected.
            node["network"]["mode"] = mode
            return node["network"]
        if mode == "auto":
            if address is not None:
                raise ValueError("auto mode cannot have explicit address")
            address = node["network"].get("address")
            if address is None:
                octet = 50 + node["index"]
                if octet > 254:
                    raise ValueError("automatic address pool exhausted")
                address = f"192.168.0.{octet}"
        elif mode != "static" or address is None:
            raise ValueError("expected auto, static or dhcp")
        ip = ipaddress.IPv4Address(address)
        if ip not in ipaddress.IPv4Network("192.168.0.0/24") or int(ip) & 255 in (0, 255):
            raise ValueError("address outside configured host range")
        address = str(ip)
        if address in others:
            raise ValueError(f"address conflict: {address}")
        node["network"] = {"mode": mode, "address": address}
        return node["network"]

    def store_composition(self, mac, composition):
        import hashlib
        raw = json.dumps(composition, sort_keys=True, separators=(",", ":"), allow_nan=False)
        digest = hashlib.sha256(raw.encode()).hexdigest()
        node = self.data["nodes"][mac_id(mac)]
        if not any(c["sha256"] == digest for c in node["compositions"]):
            node["compositions"].append({"sha256": digest, "definition": json.loads(raw)})
        return digest

    def restore(self, mac, digest):
        node = self.data["nodes"][mac_id(mac)]
        for item in node["compositions"]:
            if item["sha256"] == digest:
                return json.loads(json.dumps(item["definition"]))
        raise KeyError(digest)
