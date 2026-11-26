import json
import tempfile
import unittest
from pathlib import Path
from node_manager.probe_builder import stage,parse_report

class ProbeBuilderTest(unittest.TestCase):
    def test_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            result=stage("ESP8266","esp8266/boards/d1_mini.json",tmp)
            self.assertFalse(result["build_ready"])
            self.assertEqual(result["fqbn"],"esp8266:esp8266:d1_mini")
            self.assertTrue((Path(tmp)/"aig_probe/src/probe/probe_config.c").is_file())
            p=result["plan"]
            data={"version":1,"mac":"02:00:00:00:00:01",
                  "i2c":[{"address":x["address"],"register":r,"value":None}
                         for x in p["i2c"] for r in (x["registers"] or [256])],
                  "gpio":{str(pin):0 for pin in p["gpio"]}}
            self.assertEqual(parse_report("AIGPROBE "+json.dumps(data),p),data)
            with self.assertRaises(ValueError): parse_report("noise",p)
