"""Resolve selected modules into a deterministic draft manifest."""
import hashlib
import json
import pathlib
import re
from .pinmap import validate

ROOT = pathlib.Path(__file__).resolve().parents[1]

def load(path):
    return json.loads((ROOT / path).read_text())

def resolve(definition):
    platforms = load("embedded/adapters/registry.json")["platforms"]
    platform = definition["platform"]
    board_path = definition["board"]
    if board_path not in platforms[platform]["boards"]:
        raise ValueError("board is not registered for platform")
    board = load("embedded/adapters/" + board_path)
    registry = load("embedded/modules/registry.json")
    instances = definition["modules"]
    validate(board, registry, definition["buses"], instances)
    inputs, commands, dependencies = [], [], set()
    for instance in instances:
        ident = instance["id"]
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", ident):
            raise ValueError("invalid module identifier")
        spec = registry["modules"][instance["module"]]
        for field in spec["inputs"]:
            inputs.append({"key": f"{spec['namespace']}:{ident}:{field['name']}", "type": field["type"]})
        for cmd in spec["commands"]:
            commands.append({"name": f"um.{ident}.{cmd['name']}"})
        dependencies.update(spec["dependencies"])
    runtime = load("embedded/structure.json")
    known = runtime["runtime"]["hardcore"]["features"]
    selected = definition.get("features", known)
    if len(set(selected)) != len(selected) or not set(selected) <= set(known):
        raise ValueError("unknown or duplicate runtime feature")
    requires = {"input": {"state"}, "cs": {"state"}, "ter": {"cs", "state"}, "routine": {"cs"}}
    for feature in selected:
        if not requires.get(feature, set()) <= set(selected):
            raise ValueError(f"missing runtime prerequisites for {feature}")
    if inputs and "input" not in selected:
        raise ValueError("input modules require input feature")
    flags = definition.get("flags", [])
    if len(set(flags)) != len(flags) or not set(flags) <= set(runtime["build"]["optional_flags"]):
        raise ValueError("invalid flags")
    if "AIGMOS_ACCESSCORE" in flags and "cs" not in selected:
        raise ValueError("AccessCore hook requires CS")
    manifest = {"version": 1, "platform": platform, "board": board_path,
                "features": [f for f in known if f in selected], "flags": sorted(flags),
                "core_features": definition.get("core_features", []),
                "modules": instances, "buses": definition["buses"],
                "inputs": inputs, "commands": commands,
                "application_commands": definition.get("application_commands", []),
                "command_bindings": definition.get("commands", {}),
                "ter": definition.get("ter", {}),
                "runtime_dependencies": [], "external_dependencies": sorted(dependencies),
                "build_ready": False}
    raw = json.dumps(manifest, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return dict(manifest, sha256=hashlib.sha256(raw.encode()).hexdigest())
