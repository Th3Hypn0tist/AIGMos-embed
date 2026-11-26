import tempfile
import unittest
from node_manager.build import prepare
from node_manager.deployment import inspect,push
from node_manager.composition import load

class DeploymentTest(unittest.TestCase):
    def test_guard(self):
        d=load("applications/aqm/compositions/esp8266.json")
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(inspect(d,tmp)["stage"],"unprepared")
            prepare(d,tmp)
            self.assertEqual(inspect(d,tmp)["stage"],"prepared")
            self.assertFalse(inspect(d,tmp)["push_allowed"])
            with self.assertRaises(ValueError): push(d,tmp)
            d["variables"]["master"]="192.168.0.19"
            self.assertEqual(inspect(d,tmp)["stage"],"stale")
