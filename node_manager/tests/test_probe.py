import unittest
from node_manager.probe import plan,generate,interpret

class ProbeTest(unittest.TestCase):
    def test_plan(self):
        p=plan("ESP8266","esp8266/boards/d1_mini.json")
        self.assertEqual(p["bus"],{"sda":4,"scl":5})
        self.assertEqual(p["gpio"],[12,13,14])
        self.assertIn("{119,208}",generate(p))
    def test_inventory(self):
        p=plan("ESP8266","esp8266/boards/d1_mini.json")
        rows=[{"address":x["address"],"register":r,"value":85 if (x["address"],r)==(119,208) else 0 if x["address"]==64 else None}
              for x in p["i2c"] for r in (x["registers"] or [256])]
        data={"version":1,"i2c":rows,"gpio":{"12":0,"13":1,"14":1}}
        result=interpret(p,data)
        self.assertIn({"module":"BMP180","address":119,"status":"id_match"},result["devices"])
        self.assertIn({"module":"Si7021","address":64,"status":"candidate"},result["devices"])
        rows.pop()
        with self.assertRaises(ValueError): interpret(p,data)
