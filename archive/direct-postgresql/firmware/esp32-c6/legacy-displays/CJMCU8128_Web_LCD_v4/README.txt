CJMCU-8128 dashboard + 20x4 LCD, ESP32-C6 / Arduino IDE

LCD: PCF8574 I2C backpack at address 0x27; same SDA/SCL wires as sensors.
Backpack assumed pin mapping P0=RS, P1=RW, P2=EN, P3=light, P4-P7=data.
Use 3.3 V for the LCD backpack on the ESP32 I2C bus. Confirm LCD's
actual VCC / backlight requirements. Do not feed 5V pullups to ESP32 pins.

LCD example (20 characters/row):
T 25.5C  eCO2 560ppm
RH 31.0% TVOC 24ppb
PRES 1000.3hPa
IP 192.168.0.50

BEFORE UPLOADING:
- Copy working WIFI_PASSWORD + STATIC_IP / STATIC_GATEWAY / STATIC_SUBNET /
  STATIC_DNS values from your CURRENT firmware. The ones in this zip are
  placeholders and may be wrong for your network.
- Keep working SDA_PIN/SCL_PIN values (GPIO4/GPIO5 in the example).
- Board: ESP32C6 Dev Module, Serial Monitor 115200 baud.
- LCD brightness/backlight alone does not prove characters are visible;
  if screen stays blank, try turning the contrast trimmer slowly.

Firmware uses only Wire.h, WiFi.h, WebServer.h and Arduino core.
The web dashboard and /api/sensors continue working.
LCD rows update on sensor poll (2 seconds), only changed lines are written.
LCD adapter 0x27 absence is nonfatal; web server still runs.

Not compiled or tested with the physical LCD/ESP32-C6 in this environment.