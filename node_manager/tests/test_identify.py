import subprocess
import tempfile
import unittest
from pathlib import Path
from node_manager.identify import identify, parse_identity
from node_manager.manager import Manager

OUTPUT="Chip is ESP8266EX\nMAC: 02:00:00:00:00:01\nDetected flash size: 4MB\n"

class IdentifyTest(unittest.TestCase):
    def test_parse(self):
        self.assertEqual(parse_identity(OUTPUT),{"platform":"ESP8266","mac":"020000000001","flash_bytes":4194304})
    def test_missing(self):
        with self.assertRaises(ValueError): parse_identity("Chip is ESP8266EX")
    def test_command(self):
        def fake(args,**kw):
            self.assertEqual(args[-1],"flash_id")
            self.assertIn("--no-stub",args)
            self.assertEqual(kw["timeout"],30)
            return subprocess.CompletedProcess(args,0,OUTPUT,"")
        result=identify("/dev/ttyUSB0","esptool.py",fake)
        self.assertEqual(result["port"],"/dev/ttyUSB0")
    def test_register(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"nodes.json"
            m=Manager(path)
            identity=dict(parse_identity(OUTPUT),port="/dev/ttyUSB0")
            node=m.register_identified(identity,"esp8266/boards/d1_mini.json")
            self.assertEqual(node["hardware"]["flash_bytes"],4194304)
            self.assertIsNone(node["active"])
            self.assertEqual(Manager(path).nodes()[0]["id"],identity["mac"])
