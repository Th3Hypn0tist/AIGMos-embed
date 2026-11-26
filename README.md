# AIGMos Embedded

Native, composition-based microcontroller runtime and generic Node Manager.
AIGMos is the technical reference implementation of AIGM, not the standard itself.

## Architecture

```text
Node Manager
  Identify → Detect Hardware → Configure → Compose → Push to node
                                     |
                              Generated firmware
                                     |
Input Module → State → Trigger → Event → Runner → Command → Output Module
```

- C99 HardCore/Core, zero external runtime dependencies by design.
- Platform SDKs and optional libraries are confined to external adapters and UserModules.
- State input namespaces: #I (physical input), #OSC (OSC input).
- Trigger, Event and Runner have separate registries. ExpressionEngine is optional and independent of TER.
- Detect Hardware and Push to node are explicit, separate operations.
- Only selected components belong in the composition.

## Start Node Manager

Linux, Python 3, from the repository root:

```sh
python3 -m node_manager
```

The current interface is a temporary terminal menu. It supports device inventory,
explicit esptool 4.x identification, node registration, probe preparation/import,
hardware and pin editing, network configuration, composition history and host
build preparation. External tools are not bundled yet. Arduino Core is the preferred external adapter backend. The planned Open Core Full Package includes a local locked toolchain for offline provisioning; the initial provisioning code is documented in [toolchains](toolchains/README.md). Push is blocked until a
target builder and verification adapter exist. See [Node Manager](node_manager/README.md).

## Status

| Component | Status |
|---|---|
| Native State, CS, TER, routines | Initial implementation; semantics/integration incomplete |
| Node Manager configuration | Initial interactive implementation |
| Probe | Tables and inventory import; target execution pending |
| ESP8266 | Optional external adapter source; SDK build and Wi-Fi setup pending |
| ESP32-C6 | Existing production firmware preserved; migration pending |
| Composition/build | C tables and host objects; target firmware pending |
| AQM | Initial OSC receiver and DB adapter; end-to-end migration pending |

No confirmed host or hardware test results yet. This is development code, not a
production-ready release.

## First reference application: AQM

ESP8266 with BMP180 and DHT11. Intended composition:

```text
$master = 192.168.0.18
Trigger interval = 5000 ms
  Event: run aqm_sample
    Runner:
      um.bmp.read
      um.dht.read
      osc.out $master #I:sensorit:data

UDP/9000 → Python System Expose → #OSC → AQM UserModule → PostgreSQL → Dashboard
```

This is the target flow, not yet executable. Existing database schema, dashboard,
laser calibration workflow and C6 production firmware are preserved.

## Development

```sh
python3 -m unittest discover -s node_manager/tests
sh embedded/tests/run.sh
python3 embedded/tests/check_runtime.py
```

- [Runtime structure](embedded/structure.json)
- [AQM wire contract](structure.json)
- [Architecture notes](embedded/README.md)
- [Full checklist](developement/EMBEDDED_TASKS.md)
- [Remaining work, prioritized](developement/EMBEDDED_REMAINING.md)
- [Implemented protocol notes](PROTOCOL.md)
