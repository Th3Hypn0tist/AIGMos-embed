import tempfile
import unittest
from pathlib import Path
from node_manager.composition import load
from node_manager.composition_editor import edit,view
from node_manager.manager import Manager

class CompositionEditorTest(unittest.TestCase):
    def test_draft(self):
        d=load("applications/aqm/compositions/esp8266.json")
        self.assertFalse(view(d)["build_ready"])
        with self.assertRaises(ValueError):
            edit(d,"pending_ter",{"events":{"e":{"trigger":"missing","commands":[]}}})
        with self.assertRaises(ValueError): edit(d,"core_features",["missing"])
        self.assertEqual(d["variables"]["master"],"192.168.0.18")
    def test_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            m=Manager(Path(tmp)/"nodes.json")
            d=load("applications/aqm/compositions/esp8266.json")
            mac="020000000001"
            m.register(mac,d["platform"],d["board"])
            m.configure(mac,d)
            first=m.history(mac)[0]["sha256"]
            m.composition_edit(mac,"variables",{"master":"192.168.0.19"})
            self.assertEqual(len(m.history(mac)),2)
            m.select(mac,first)
            self.assertEqual(m.selected(mac),d)
            self.assertFalse(any(x["active"] for x in m.history(mac)))
