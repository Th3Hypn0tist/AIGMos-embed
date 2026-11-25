ESP32-C6 + CJMCU-8128 + LCD2004A v5 LCD diagnostic

Changes vs v4:
- Conservative HD44780 4-bit initialization and longer E pulse/data delays.
- I2C clock temporarily selected as 50 kHz for diagnostic stability.
- At power-on, the LCD shows four numbered 20-character lines for five seconds.
- Then original web dashboard and sensor monitor continue as before.
- No external Arduino LCD libraries required.

To test:
1) Before opening, copy your working IOT Wi-Fi password and STATIC_IP / GATEWAY / SUBNET / DNS from the previous sketch.
2) GPIO4=SDA and GPIO5=SCL, LCD PCF8574 address 0x27.
3) Fully remove power from LCD and ESP32-C6, reconnect power.
4) Watch four-row test within the first few seconds, then the live dashboard.

Expected test:
ROW1 0123456789 ABCD
ROW2 0123456789 ABCD
ROW3 0123456789 ABCD
ROW4 0123456789 ABCD

If only rows 1 and 3 show random characters again, it may be a pin mapping or LCD controller power/initialization problem, not just contrast. Verify PCF8574-to-HD44780 pin mapping and use a proper bidirectional I2C level shifter before trying a 5V supply on LCD backpack. Do not wire 5V SDA/SCL directly to ESP32-C6.

Hardware not verified. The I2C address ACK confirms only the expander, not the LCD controller.