import pathlib
import tempfile
import unittest
from node_manager.registry import Registry
from node_manager.composition import load, resolve

class RegistryTest(unittest.TestCase):
    def test_persistence(self):
        with tempfile.TemporaryDirectory() as folder:
            path = pathlib.Path(folder) / "nodes.json"
            r = Registry(path)
            a = "00:11:22:33:44:55"
            b = "00:11:22:33:44:56"
            r.register(a, "ESP8266", "d1_mini")
            r.register(b, "ESP8266", "d1_mini")
            self.assertEqual(r.network(a, "auto")["address"], "192.168.0.51")
            self.assertEqual(r.network(b, "auto")["address"], "192.168.0.52")
            r.network(a, "dhcp")
            with self.assertRaises(ValueError):
                r.network(b, "static", "192.168.0.51")
            digest = r.store_composition(b, {"version": 1})
            r.save()
            r = Registry(path)
            self.assertEqual(r.network(a, "auto")["address"], "192.168.0.51")
            self.assertEqual(r.restore(b, digest), {"version": 1})
    def test_composition(self):
        d = load("applications/aqm/compositions/esp8266.json")
        a = resolve(d)
        self.assertEqual(a, resolve(d))
        self.assertEqual(len(a["inputs"]), 4)
        self.assertFalse(a["build_ready"])
        d["features"] = ["state", "input", "ter"]
        with self.assertRaises(ValueError):
            resolve(d)
