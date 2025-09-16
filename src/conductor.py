# main.py
# Runs on the Raspberry Pi Pico W
# Plays a simple melody through a buzzer connected to a GPIO pin

from machine import Pin, PWM
import time

# --- Configuration ---
BUZZER_PIN = 18  # Change to the pin your buzzer is connected to
buzzer = PWM(Pin(BUZZER_PIN))

# --- Notes ---
C4 = 262
D4 = 294
E4 = 330
F4 = 349
G4 = 392
A4 = 440
B4 = 494
C5 = 523

# --- Melody ---
SONG = [
    (C4, 400),
    (C4, 400),
    (G4, 400),
    (G4, 400),
    (A4, 400),
    (A4, 400),
    (G4, 800),
    (F4, 400),
    (F4, 400),
    (E4, 400),
    (E4, 400),
    (D4, 400),
    (D4, 400),
    (C4, 800),
]

# --- Functions ---
def play_note(freq, ms):
    if freq == 0:  # Rest
        buzzer.duty_u16(0)
    else:
        buzzer.freq(freq)
        buzzer.duty_u16(32768)  # 50% duty cycle
    time.sleep_ms(ms)
    buzzer.duty_u16(0)  # Stop sound
    time.sleep_ms(50)   # Short gap between notes


# --- Main Loop ---
print("Starting melody...")
for freq, duration in SONG:
    play_note(freq, duration)

print("Song finished!")
buzzer.deinit()
