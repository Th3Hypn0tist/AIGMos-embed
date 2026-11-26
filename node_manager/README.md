# Node Manager

Run from the repository root with Python 3:

    python3 -m node_manager

The first terminal surface uses only the Python standard library. Registry:
`~/.config/aigmos-embed/nodes.json` (override with --registry).
USB inventory is passive Linux serial enumeration. Identify MCU (menu 10) explicitly uses an external esptool 4.x CLI to read chip, MAC and flash size; it may reset the selected device but does not write flash. Board selection remains explicit. Menu 11 reports toolchain executables found on PATH; it does not verify SDK compatibility.
Register known MAC/platform/board manually, select network mode, import a
composition, and inspect or prepare its draft build. Example:
`applications/aqm/compositions/esp8266.json`.

Prepare build is not Push to node. No firmware is flashed and no active
composition is set. Hardware probe, target build, interactive pin editor
and final AIGMos Panel integration are outstanding. The AQM pending_ter
field documents intended commands; it is not executable yet.

Menu 14 edits a node's hardware composition. It displays GPIO ownership, reserved and strap pins, module requirements and imported probe candidates. Each successful edit creates/selects a validated composition version; it never changes active firmware. Probe candidates are not selected automatically. Live hardware tests are not yet available.

Menu 4 provides network configuration. Linux neighbor cache is advisory, not a complete conflict scan; ping does not validate OSC. Wi-Fi credentials are stored separately in a local private file (plaintext, mode 0600), not in the composition or registry. Keep the registry outside Git. ESP8266 allocation starts at index 1 (.51); index 0/.50 is reserved for legacy C6. Existing registry indices are not migrated automatically. Target Wi-Fi and OSC integration remain pending.
