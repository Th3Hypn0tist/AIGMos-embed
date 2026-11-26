"""Validate explicit bindings against board and module metadata."""
def validate(board, registry, buses, instances):
    used = {}
    addresses = set()
    names = set()
    def claim(pin, owner, capability):
        if type(pin) is not int:
            raise ValueError("GPIO must be an integer")
        meta = board["pins"].get(str(pin), {})
        if pin in board.get("reserved", []) or str(pin) in board.get("strap", {}) or capability not in meta.get("capabilities", []):
            raise ValueError(f"GPIO {pin} unavailable for {owner}")
        if pin in used:
            raise ValueError(f"GPIO {pin} conflict: {used[pin]} / {owner}")
        used[pin] = owner
    for name, bus in buses.items():
        if bus["kind"] != "i2c":
            raise ValueError("unsupported bus")
        claim(bus["sda"], name + ":sda", "i2c")
        claim(bus["scl"], name + ":scl", "i2c")
    for item in instances:
        name = item["id"]
        if not name or name in names:
            raise ValueError("duplicate or empty instance id")
        names.add(name)
        spec = registry["modules"][item["module"]]
        binding = item["bindings"]
        if spec["interface"] == "i2c":
            bus, address = binding["bus"], binding["address"]
            if bus not in buses or type(address) is not int or address not in spec["bindings"]["address"]:
                raise ValueError(f"invalid I2C binding: {name}")
            key = (bus, address)
            if key in addresses:
                raise ValueError(f"I2C address conflict: {key}")
            addresses.add(key)
        elif spec["interface"] == "gpio":
            claim(binding["data"], name, "gpio")
        else:
            raise ValueError("unsupported interface")
    return used
