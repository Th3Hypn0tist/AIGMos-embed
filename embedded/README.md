# AIGMos-embed

Native runtime baseline: C99, no external libraries or platform SDK in HardCore or Core. C++ adapters may link through C ABI. Runtime state is caller-owned; no required heap, network, OS or Arduino. Input modules write State under #I; TER runs commands; output modules execute commands. Platform SDKs and user modules are outside runtime. Existing firmware remains untouched until AQM migration is verified.

`structure.json` defines the initial runtime boundaries; existing root structure.json remains the AQM wire contract.
