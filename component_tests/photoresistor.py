# Reads the photoresistor value and changes the pitch based on brightness.

from machine import ADC, Pin, PWM
import time

# --- Hardware Setup ---
photo_sensor = ADC(28)          # Photoresistor on GP28 (ADC0)
buzzer = PWM(Pin(18))           # Passive buzzer on GP18

# --- Frequency Mapping ---
MIN_LIGHT = 1000     # Dark threshold
MAX_LIGHT = 65000    # Bright threshold
MIN_FREQ = 261       # C4
MAX_FREQ = 1046      # C6

def map_value(x, in_min, in_max, out_min, out_max):
    """Maps a value from one range to another."""
    return int((x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)

def stop_tone():
    buzzer.duty_u16(0)

def play_from_light():
    """Reads light sensor and maps brightness to a tone."""
    light_val = photo_sensor.read_u16()
    clamped = max(MIN_LIGHT, min(light_val, MAX_LIGHT))

    if clamped > MIN_LIGHT:
        freq = map_value(clamped, MIN_LIGHT, MAX_LIGHT, MIN_FREQ, MAX_FREQ)
        buzzer.freq(freq)
        buzzer.duty_u16(32768)  # 50% duty cycle
    else:
        stop_tone()

# --- Main Loop ---
print("Lumosynth starting... shine light on the sensor to hear tones!")

try:
    while True:
        play_from_light()
        time.sleep(0.05)
except KeyboardInterrupt:
    print("Stopped by user.")
    stop_tone()
    buzzer.deinit()
