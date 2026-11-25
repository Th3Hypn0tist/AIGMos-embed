CJMCU-8128 / ESP32-C6 / OLED v7

Fix v6 -> v7: All 43 OLED_FONT array rows had their commas inside comments, causing C++ compilation error "expected } before { token". The commas are now part of the C++ initializer.

Arduino IDE: open CJMCU8128_Web_OLED_v7.ino, choose ESP32C6 Dev Module, select COM port.
Wi-Fi: SSID IOT; default password empty; static IP 192.168.0.50. Check gateway and DNS.
I2C pins: GPIO4 SDA / GPIO5 SCL, OLED: 0x3C. Other sensors: 0x40 / 0x5A / 0x76.
OLED: 128x64, default SSD1306; set OLED_SH1106=true if your OLED uses SH1106.
Built-in Arduino ESP32 WiFi/WebServer/Wire libraries only.

Note: compilation against the exact Arduino-ESP32 core / physical hardware not tested in this environment.