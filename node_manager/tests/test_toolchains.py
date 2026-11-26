import json
import tempfile
import unittest
from pathlib import Path
from node_manager.toolchains import configure,cli,inventory

class ToolchainTest(unittest.TestCase):
    def test_local_paths(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp)
            (home/"manifest.json").write_text(json.dumps({"arduino_cli":{"path":"bin/arduino-cli"},"cores":[]}))
            cfg=json.loads(configure(home).read_text())
            self.assertEqual(cfg["directories"]["data"],str(home/"data"))
            with self.assertRaises(ValueError): cli(home)
            (home/"bin").mkdir()
            (home/"bin/arduino-cli").write_bytes(b"test")
            self.assertIn("bin/arduino-cli",inventory(home)["files"])
