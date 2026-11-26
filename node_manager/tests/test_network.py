import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from node_manager.network import neighbors,occupied,endpoint,wifi
from node_manager.manager import Manager

class NetworkTest(unittest.TestCase):
    def test_neighbor(self):
        def fake(*args,**kwargs):
            return subprocess.CompletedProcess(args,0,json.dumps([{"dst":"192.168.0.51","lladdr":"02:00:00:00:00:02","state":["STALE"]}]),"")
        self.assertEqual(occupied(neighbors(fake),"020000000001"),{"192.168.0.51"})
    def test_configuration(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=Manager(Path(tmp)/"nodes.json")
            mac="020000000001"
            m.register(mac,"ESP8266","esp8266/boards/d1_mini.json")
            self.assertEqual(m.network(mac,"auto")["address"],"192.168.0.51")
            with self.assertRaises(ValueError): m.network(mac,"static","192.168.0.50")
            m.set_wifi(mac,"test","password123")
            self.assertNotIn("password123",m.registry.path.read_text())
            self.assertTrue(m.network_view(mac)["wifi_configured"])
            m.set_endpoint(mac,"192.168.0.18",9000)
            self.assertEqual(m.selected(mac)["variables"]["master"],"192.168.0.18")
    def test_validation(self):
        with self.assertRaises(ValueError): endpoint("192.168.0.18",0)
        with self.assertRaises(ValueError): wifi("test","short")
