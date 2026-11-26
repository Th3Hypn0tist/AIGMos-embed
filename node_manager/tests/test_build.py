import shutil
import tempfile
import unittest
from pathlib import Path
from node_manager.build import plan, compile_objects
from node_manager.composition import load

def definition():
    d=load("applications/aqm/compositions/esp8266.json")
    d["features"]=["state","input","cs","ter"]
    d["core_features"]=["validate"]
    d["application_commands"]=["um.aqm.send"]
    d["commands"]={"um.aqm.send":"aqm_send"}
    d["ter"]={"triggers":{"sample":{"condition":"sample_due"}},
              "events":{"send":{"trigger":"sample","commands":[{"command":"um.aqm.send","args":[None,True,-2,1.25]}]}}}
    return d

class BuildTest(unittest.TestCase):
    def test_plan(self):
        d=definition()
        manifest,code=plan(d)
        self.assertNotIn("embedded/hardcore/routine.c",manifest["runtime_sources"])
        self.assertIn("embedded/core/validate.c",manifest["runtime_sources"])
        self.assertIn("AIG_INT,{.integer=-2LL}",code)
        self.assertFalse(manifest["build_ready"])
        self.assertIn("embedded/modules/bmp180/bmp180.c",manifest["module_sources"])
        self.assertIn("embedded/modules/dht11/dht11.c",manifest["module_sources"])
        self.assertEqual((manifest,code),plan(d))
    @unittest.skipUnless(shutil.which("cc"),"host compiler missing")
    def test_compile(self):
        with tempfile.TemporaryDirectory() as folder:
            result=compile_objects(definition(),folder)
            self.assertEqual(len(list(Path(folder).glob("*.o"))),len(result["runtime_sources"])+len(result["module_sources"])+1)
