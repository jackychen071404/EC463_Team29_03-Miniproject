# main.py
# Simple RGB LED demo with debug prints
# Red: GP21, Green: GP20, Blue: GP19

from machine import Pin, PWM
import time

# --- Setup PWM pins ---
red = PWM(Pin(21))
green = PWM(Pin(20))
blue = PWM(Pin(19))

# Set PWM frequency (1 kHz is fine for LEDs)
red.freq(1000)
green.freq(1000)
blue.freq(1000)

def set_color(r, g, b):
    """Set RGB color. Values 0-65535."""
    red.duty_u16(r)
    green.duty_u16(g)
    blue.duty_u16(b)
    print(f"Set color -> R:{r} G:{g} B:{b}")

try:
    while True:
        print("Red ON")
        set_color(65535, 0, 0)
        time.sleep(1)

        print("Green ON")
        set_color(0, 65535, 0)
        time.sleep(1)

        print("Blue ON")
        set_color(0, 0, 65535)
        time.sleep(1)

        print("White ON")
        set_color(65535, 65535, 65535)
        time.sleep(1)

        print("All OFF")
        set_color(0, 0, 0)
        time.sleep(1)

except KeyboardInterrupt:
    print("Stopping program and turning off LEDs...")
    set_color(0, 0, 0)
    red.deinit()
    green.deinit()
    blue.deinit()
