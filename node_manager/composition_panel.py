"""Standalone composition view and section editor."""
import json
from .composition import load

def run(manager,mac,show):
    sections=("features","core_features","flags","variables","application_commands","commands","ter","pending_ter")
    while True:
        print("\nComposition Manager")
        show(manager.composition_view(mac))
        print("1 Edit section  2 Version history  3 Restore version  4 Feature registry  0 Back")
        try:
            action=input("> ").strip()
            if action=="0": return
            if action=="1":
                print("Sections:",", ".join(sections))
                section=input("Section: ").strip()
                if section not in sections: raise ValueError("unknown section")
                definition=manager.hardware_definition(mac)
                show(definition.get(section,[] if section in ("features","core_features","flags","application_commands") else {}))
                value=json.loads(input("Replacement JSON (single line): "))
                show(manager.composition_edit(mac,section,value))
            elif action=="2": show(manager.history(mac))
            elif action=="3":
                show(manager.history(mac))
                manager.select(mac,input("Version SHA-256: ").strip())
            elif action=="4": show(load("embedded/structure.json"))
            else: print("Unknown action")
        except (ValueError,KeyError,TypeError,OSError) as exc: print("ERROR:",exc)
