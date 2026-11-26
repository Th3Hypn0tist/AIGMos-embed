# ESP8266 adapter

First optional backend: ESP8266 Arduino core, confined to this external adapter.
Arduino is not a runtime requirement. The adapter implements the C ABI for
GPIO, one I2C bus, UART0, monotonic time, delay and IPv4 UDP. Wi-Fi association,
static/DHCP configuration, SDK build integration and flash operations are not
implemented yet. UART0 pins and boot strap pins are deliberately unavailable
for GPIO in this backend; GPIO16 has limited capabilities. Time extension
requires polling at least once per micros wrap. DHT pulse timing under Wi-Fi
load requires hardware verification. This adapter has not been compiled against
the target SDK. A non-Arduino SDK backend remains possible.
