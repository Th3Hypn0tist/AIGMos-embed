import tempfile
import unittest
from pathlib import Path
from node_manager.manager import Manager
from node_manager.composition import load
from node_manager.discovery import serial_ports

class ManagerTest(unittest.TestCase):
    def test_configure_persist(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"nodes.json"
            manager=Manager(path)
            d=load("applications/aqm/compositions/esp8266.json")
            mac="02:00:00:00:00:01"
            manager.register(mac,d["platform"],d["board"])
            manager.network(mac,"auto")
            manager.configure(mac,d)
            self.assertEqual(Manager(path).selected(mac),d)
            self.assertEqual(Manager(path).nodes()[0]["network"]["address"],"192.168.0.51")
    def test_serial_inventory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"ttyUSB0").touch()
            self.assertEqual(serial_ports(root,root)[0]["identified"],False)
