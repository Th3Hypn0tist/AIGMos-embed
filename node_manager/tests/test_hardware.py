import unittest
import tempfile
from pathlib import Path
from node_manager.hardware import blank,edit,pinout,available
from node_manager.manager import Manager

NODE={"platform":"ESP8266","board":"esp8266/boards/d1_mini.json"}

class HardwareTest(unittest.TestCase):
    def test_edit(self):
        d=blank(NODE)
        d=edit(d,"bus",name="main",sda=4,scl=5)
        d=edit(d,"add",id="bmp",module="BMP180",bindings={"bus":"main","address":119})
        d=edit(d,"add",id="dht",module="DHT11",bindings={"data":14})
        self.assertNotIn(14,[p["gpio"] for p in available(d,"gpio")])
        self.assertTrue(next(p for p in pinout(d) if p["gpio"]==0)["blocked"])
        with self.assertRaises(ValueError): edit(d,"bind",id="dht",bindings={"data":4})
        with self.assertRaises(ValueError): edit(d,"remove_bus",name="main")
        self.assertEqual(d["modules"][1]["bindings"]["data"],14)
        d=edit(d,"replace",id="bmp",module="BMP280",bindings={"bus":"main","address":118})
        d=edit(d,"remove",id="bmp")
        self.assertEqual(len(d["modules"]),1)
    def test_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"nodes.json"
            m=Manager(path)
            mac="02:00:00:00:00:01"
            m.register(mac,NODE["platform"],NODE["board"])
            m.hardware_edit(mac,"bus",name="main",sda=4,scl=5)
            self.assertEqual(Manager(path).selected(mac)["buses"]["main"]["sda"],4)
            self.assertIsNone(Manager(path).nodes()[0]["active"])
