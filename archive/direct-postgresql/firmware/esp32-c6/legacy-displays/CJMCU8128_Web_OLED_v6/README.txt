CJMCU-8128 + ESP32-C6 + 128x64 I2C OLED (v6)

Arduino IDE: Board ESP32C6 Dev Module, ESP32 core 3.x
No external libraries: Wire, WiFi, WebServer included with ESP32 core.

Hardware:
  OLED GND -> GND
  OLED VCC -> 3V3 (not 5V)
  OLED SDA -> GPIO4 (shared with CJMCU-8128)
  OLED SCL -> GPIO5 (shared with CJMCU-8128)
  CJMCU-8128 WAK -> GND

I2C scan expected: 0x3C 0x40 0x5A 0x76
OLED controller default: SSD1306 128x64, I2C 0x3C.
If the module is SH1106 and screen is blank or shifted, change OLED_SH1106 to true.
If your module is 128x32, this firmware's 128x64 layout must be adapted.

Wi-Fi: set WIFI_PASSWORD (empty for open network).
Static IP defaults to 192.168.0.50; VERIFY gateway and DNS values
(the example sets 192.168.0.1) against your router's actual configuration.

HTTP dashboard: http://192.168.0.50/
JSON API: http://192.168.0.50/api/sensors
Serial Monitor: 115200.

LCD 2004A code removed. Sensor and HTTP functionality carried over from v5.
OLED functions written directly using Wire.h. Refresh every 2 seconds.

NOTE: Not tested on physical hardware. OLED type cannot be definitively
identified from I2C address alone; SSD1306 is the initial assumption.