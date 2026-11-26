import unittest
from node_manager.composition import load
from node_manager.generator import generate

class GeneratorTest(unittest.TestCase):
    def definition(self):
        d=load("applications/aqm/compositions/esp8266.json")
        d["application_commands"]=["um.aqm.send"]
        d["commands"]={"um.aqm.send":"aqm_send"}
        d["ter"]={"triggers":{"sample":{"condition":"sample_due"}},
                  "events":{"send":{"trigger":"sample","commands":["um.aqm.send"]}},
                  "runners":{}}
        return d
    def test_tables(self):
        d=self.definition()
        c=generate(d)
        self.assertIn("aig_trigger triggers[]",c)
        self.assertIn("const aig_event events[]",c)
        self.assertIn("#I:bmp:temperature_c",c)
        self.assertEqual(c,generate(d))
    def test_bad_reference(self):
        d=self.definition()
        d["ter"]["events"]["send"]["trigger"]="missing"
        with self.assertRaises(ValueError): generate(d)
    def test_bad_handler(self):
        d=self.definition()
        d["commands"]["um.aqm.send"]="bad();"
        with self.assertRaises(ValueError): generate(d)
