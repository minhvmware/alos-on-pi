# MicroPython USB-UART bridge for Raspberry Pi Pico (RP2040).
#
# Wiring (Pi 5 <-> Pico):
#   Pi pin 6  GND  <-> Pico GND
#   Pi pin 8  TXD  <-> Pico GP1 (UART0 RX)
#   Pi pin 10 RXD  <-> Pico GP0 (UART0 TX)   [optional for one-way capture]
#
# Do NOT connect Pico 3V3 to Pi. Pico is powered by its own USB cable.
# Copy this file to the Pico as "main.py". Laptop sees /dev/ttyACM0.

import machine
import sys
import time

uart = machine.UART(
    0,
    baudrate=115200,
    bits=8,
    parity=None,
    stop=1,
    tx=machine.Pin(0),
    rx=machine.Pin(1),
    timeout=0,
)

while True:
    n = uart.any()
    if n:
        data = uart.read(n)
        if data:
            sys.stdout.write(data.decode("utf-8", "replace"))
    else:
        time.sleep_ms(2)
