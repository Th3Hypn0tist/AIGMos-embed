# Local toolchain (development baseline)

Arduino Core is the preferred external platform backend, not an AIGMos runtime dependency.
Initial host: Linux x86-64. Candidate version pins are in manifest.json; target compatibility has not been verified.

Place the exact Arduino CLI executable in bin/arduino-cli after verifying the upstream release checksum.
Run from repository root:

    python3 -m node_manager.toolchains install
    python3 -m node_manager.toolchains status
    python3 -m node_manager.toolchains inventory

Install is an explicit online operation. Normal status and inventory do not request index updates.
The CLI uses a generated local config, with no fallback to a system Arduino CLI.
Configuration is regenerated for the current absolute location after relocation.

Source Package contains code and provisioning instructions. Full Package is planned to include
CLI, cores, compiler/flash tools, license notices, corresponding sources and required relinking
materials. Binary/source downloads are not committed to Git. Inventory hashes are local observations,
not independently authenticated upstream hashes. Release packaging, signed/checksummed upstream
bootstrap, transitive tool lock, license audit, offline build tests and standalone esptool packaging
remain open. No Full Package is produced by this baseline.
