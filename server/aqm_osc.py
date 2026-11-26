"""AQM OSC receiver. Run on trusted IOT LAN only."""
import argparse
import json
import logging
import math
import os
import re
import socket
import struct
from pathlib import Path

SPEC = json.loads((Path(__file__).resolve().parents[1] / "structure.json").read_text())
FIELDS = SPEC["fields"]
SQL = "SELECT aqm.ingest(" + ",".join("%s::" + f[2] for f in FIELDS) + ")"

def decode(packet):
    # One immediate OSC bundle with one atomic sample message.
    if len(packet) < 20 or packet[:16] != b"#bundle\0" + struct.pack(">Q", 1):
        raise ValueError("expected immediate bundle")
    size = struct.unpack_from(">I", packet, 16)[0]
    if size != len(packet) - 20:
        raise ValueError("invalid bundle length")
    data = packet[20:]
    pos = 0
    def string():
        nonlocal pos
        end = data.index(b"\0", pos)
        value = data[pos:end].decode("utf-8")
        next_pos = (end + 4) & ~3
        if next_pos > len(data) or any(data[end:next_pos]):
            raise ValueError("invalid string padding")
        pos = next_pos
        return value
    def number(fmt):
        nonlocal pos
        value = struct.unpack_from(fmt, data, pos)[0]
        pos += struct.calcsize(fmt)
        return value
    if string() != SPEC["address"]:
        raise ValueError("unknown address")
    tags = string()
    if not tags.startswith(",") or len(tags) != len(FIELDS) + 2 or tags[1] != "i":
        raise ValueError("invalid type tags")
    if number(">i") != SPEC["version"]:
        raise ValueError("unsupported version")
    values = []
    for tag, field in zip(tags[2:], FIELDS):
        name, kind, _ = field[:3]
        if tag == "N" and len(field) == 4 and field[3]:
            value = None
        elif kind == "bool" and tag in ("T", "F"):
            value = tag == "T"
        elif kind == tag:
            value = string() if tag == "s" else number({"i":">i","h":">q","f":">f"}[tag])
            if isinstance(value, float) and not math.isfinite(value):
                raise ValueError(name)
        else:
            raise ValueError("invalid type: " + name)
        values.append(value)
    if pos != len(data):
        raise ValueError("trailing data")
    if not re.fullmatch("[0-9a-f]{12}", values[0]) or not re.fullmatch("[0-9a-f]{16}", values[3]):
        raise ValueError("invalid identity")
    if min(values[4:6]) < 0:
        raise ValueError("negative counter")
    return values

def main():
    import psycopg
    parser = argparse.ArgumentParser()
    parser.add_argument("--bind", required=True, help="IOT interface IPv4")
    parser.add_argument("--port", type=int, default=9000)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    dsn = os.environ["AQM_DSN"]
    conn = None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((args.bind, args.port))
        while True:
            packet, peer = sock.recvfrom(4096)
            try:
                values = decode(packet)
                if conn is None or conn.closed:
                    conn = psycopg.connect(dsn, autocommit=True, connect_timeout=3)
                inserted = conn.execute(SQL, values).fetchone()[0]
                logging.info("%s seq=%s inserted=%s", values[0], values[4], inserted)
            except (ValueError, struct.error) as exc:
                logging.warning("Invalid packet from %s: %s", peer, exc)
            except psycopg.Error as exc:
                logging.error("Database error: %s", exc)
                if conn is not None:
                    conn.close()
                conn = None

if __name__ == "__main__":
    main()
