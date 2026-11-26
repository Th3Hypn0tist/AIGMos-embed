#!/usr/bin/env python3
"""Conservative source include boundary check; not a linker audit."""
import pathlib
import re
import sys

root = pathlib.Path(__file__).resolve().parents[1]
allowed = {root / "hardcore", root / "core"}
standard = {"stddef.h", "stdint.h"}
errors = []
for folder in sorted(allowed):
    for path in sorted(folder.rglob("*")):
        if path.suffix not in {".c", ".h"}:
            continue
        for line in path.read_text().splitlines():
            if not re.match(r"\s*#\s*include\b", line):
                continue
            match = re.fullmatch(r'\s*#\s*include\s*([<"])([^>"]+)[>"]\s*', line)
            if not match:
                errors.append(f"{path}: unrecognized include: {line}")
                continue
            kind, name = match.groups()
            if kind == "<" and name in standard:
                continue
            target = (path.parent / name).resolve()
            if kind == '"' and target.is_file() and any(p in target.parents for p in allowed):
                if folder.name != "hardcore" or root / "hardcore" in target.parents:
                    continue
            errors.append(f"{path}: forbidden include: {name}")
if errors:
    print("\n".join(errors), file=sys.stderr)
    sys.exit(1)
print("Runtime include boundaries OK")
