# conductor.py
# Runs on a student's computer (not the Pico)
# Requires the 'requests' library: pip install requests

import requests
from requests.exceptions import Timeout, RequestException
import time

# --- Configuration ---
# Populate this list with the IP addresses of your Pico devices
PICO_IPS = [
    "192.168.1.101",  # Example, replace with your Pico IPs
]

# --- Notes (frequencies in Hz) ---
C3 = 131
D3 = 147
E3 = 165
F3 = 175
G3 = 196
A3 = 220
B3 = 247

C4 = 262
C4Sharp = 277
D4 = 294
D4Sharp = 311
E4 = 330
F4 = 349
F4Sharp = 370
G4 = 392
G4Sharp = 415
A4 = 440
A4Sharp = 466
B4 = 494
B4Sharp = 523
C5 = 523

Db3 = 139
Eb3 = 156
Gb3 = 185
Ab3 = 208
Bb3 = 233

Db4 = 277
Eb4 = 311
Gb4 = 370
Ab4 = 415
Bb4 = 466

Db5 = 554
Eb5 = 622
Gb5 = 740
Ab5 = 831
Bb5 = 932

# --- Melody: "Mary Had a Little Lamb" with variable note durations ---
# Format: (frequency_in_Hz, duration_in_ms)
SONG = [
    (F4, 400), (C3, 400),
    (Ab4, 400), (C3, 400),
    (Gb4, 400), (C3, 400),
    (Eb4, 400), (C3, 400),
    (C5, 800)
]

# --- Conductor Functions ---
def play_note_on_all_picos(freq, ms, duty=0.5):
    """Send a /tone POST request to all Pico devices."""
    print(f"Playing {freq}Hz for {ms}ms on all devices.")
    payload = {"freq": freq, "ms": ms, "duty": duty}

    for ip in PICO_IPS:
        url = f"http://{ip}/tone"
        try:
            # Short timeout keeps notes in sync
            requests.post(url, json=payload, timeout=0.1)
        except Timeout:
            pass  # Expected for non-blocking playback
        except RequestException as e:
            print(f"Error contacting {ip}: {e}")

# Optional: send a full melody in one request (requires Pico Device Service support)
def play_melody_on_all_picos(notes, gap_ms=20):
    """Send a /melody POST request to all Pico devices."""
    payload = {"notes": [{"freq": f, "ms": ms} for f, ms in notes], "gap_ms": gap_ms}
    for ip in PICO_IPS:
        url = f"http://{ip}/melody"
        try:
            requests.post(url, json=payload, timeout=0.1)
        except RequestException as e:
            print(f"Error contacting {ip}: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    print("--- Pico Light Orchestra Conductor ---")
    print(f"Found {len(PICO_IPS)} devices in the orchestra.")
    print("Press Ctrl+C to stop.")

    try:
        # Countdown before starting
        print("\nStarting in 3...")
        time.sleep(1)
        print("2...")
        time.sleep(1)
        print("1...")
        time.sleep(1)
        print("Go!\n")

        # Play each note individually
        for note, duration in SONG:
            play_note_on_all_picos(note, duration)
            # Wait for note duration + small gap
            time.sleep(duration / 1000 * 1.1)

        print("\nSong finished!")

    except KeyboardInterrupt:
        print("\nConductor stopped by user.")