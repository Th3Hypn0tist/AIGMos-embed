import json
import pathlib
import unittest
from node_manager.pinmap import validate

ROOT = pathlib.Path(__file__).resolve().parents[2]
BOARD = json.loads((ROOT / "embedded/adapters/esp8266/boards/d1_mini.json").read_text())
REG = json.loads((ROOT / "embedded/modules/registry.json").read_text())
BUS = {"main": {"kind": "i2c", "sda": 4, "scl": 5}}
BMP = {"id": "bmp", "module": "BMP180", "bindings": {"bus": "main", "address": 119}}
DHT = {"id": "dht", "module": "DHT11", "bindings": {"data": 14}}

class PinmapTest(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(set(validate(BOARD, REG, BUS, [BMP, DHT])), {4, 5, 14})
    def test_conflict(self):
        with self.assertRaises(ValueError):
            validate(BOARD, REG, BUS, [BMP, dict(DHT, bindings={"data": 4})])
    def test_address_conflict(self):
        with self.assertRaises(ValueError):
            validate(BOARD, REG, BUS, [BMP, dict(BMP, id="other")])
    def test_strap(self):
        with self.assertRaises(ValueError):
            validate(BOARD, REG, BUS, [dict(DHT, bindings={"data": 0})])

if __name__ == "__main__":
    unittest.main()
