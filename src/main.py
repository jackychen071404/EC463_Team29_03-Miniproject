import machine
import network
import time
import uasyncio as asyncio
import json
import ubinascii

# -------------------------
# Hardware Setup
# -------------------------
PHOTO_SENSOR_PIN = 28
BUZZER_PIN = 18

photo_sensor = machine.ADC(PHOTO_SENSOR_PIN)
buzzer = machine.PWM(machine.Pin(BUZZER_PIN))
buzzer.freq(440)
buzzer.duty_u16(0)  # Start silent

# -------------------------
# RGB LED Setup
# -------------------------
red = machine.PWM(machine.Pin(21))
green = machine.PWM(machine.Pin(20))
blue = machine.PWM(machine.Pin(19))

red.freq(1000)
green.freq(1000)
blue.freq(1000)

# Global color state
current_color = (0, 0, 0)

def set_color(r, g, b):
    global current_color
    current_color = (r, g, b)
    red.duty_u16(r)
    green.duty_u16(g)
    blue.duty_u16(b)
    print(f"Set color -> R:{r} G:{g} B:{b}")

# -------------------------
# Device Identification
# -------------------------
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
DEVICE_ID = ubinascii.hexlify(wlan.config("mac")).decode()

# -------------------------
# Wi-Fi Configuration
# -------------------------
SSID = "BU Guest (unencrypted)"  # Replace with your SSID
PASSWORD = ""                     # Empty if open network

print("Connecting to Wi-Fi...")
wlan.connect(SSID, PASSWORD)
while not wlan.isconnected():
    time.sleep(1)
IP_ADDRESS = wlan.ifconfig()[0]
print(f"Connected! IP address: {IP_ADDRESS}")

# -------------------------
# Global Async Task Tracking
# -------------------------
current_task = None  # Will store the currently playing tone/melody

# -------------------------
# Light-to-frequency mapping
# -------------------------
MIN_LIGHT = 1000
MAX_LIGHT = 65000
MIN_FREQ = 261  # C4
MAX_FREQ = 1046 # C6

def map_value(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) // (in_max - in_min) + out_min)

def read_light_sensor():
    raw = photo_sensor.read_u16()
    norm = raw / 65535
    lux_est = norm * 200
    return {"raw": raw, "norm": round(norm, 3), "lux_est": round(lux_est, 1)}

def stop_buzzer():
    buzzer.duty_u16(0)
    print("[Buzzer] Stopped")

# -------------------------
# Tone and Melody
# -------------------------
async def play_tone(freq, duration_ms):
    """Play tone with immediate light-based volume and frequency mapping."""
    if freq <= 0 or duration_ms <= 0:
        return

    buzzer.freq(freq)
    step_ms = 50
    elapsed = 0

    while elapsed < duration_ms:
        light_val = photo_sensor.read_u16()
        clamped = max(MIN_LIGHT, min(light_val, MAX_LIGHT))
        if clamped > MIN_LIGHT:
            new_freq = map_value(clamped, MIN_LIGHT, MAX_LIGHT, MIN_FREQ, MAX_FREQ)
            buzzer.freq(new_freq)
            buzzer.duty_u16(32768)  # 50% duty for clarity
        else:
            stop_buzzer()

        await asyncio.sleep_ms(step_ms)
        elapsed += step_ms

    stop_buzzer()

async def play_melody(notes, gap_ms=20):
    print(f"[Melody] Starting {len(notes)} notes")
    for i, note in enumerate(notes, start=1):
        freq = note.get("freq", 0)
        duration = note.get("ms", 200)
        print(f"[Melody] Note {i}/{len(notes)}: {freq}Hz for {duration}ms")
        await play_tone(freq, duration)
        await asyncio.sleep_ms(gap_ms)
    print("[Melody] Finished")

# -------------------------
# LED Helper
# -------------------------
async def blink_led(r, g, b, duration_ms=500):
    global current_color
    original_color = current_color
    set_color(r, g, b)
    elapsed = 0
    step = 50
    while elapsed < duration_ms:
        await asyncio.sleep_ms(step)
        elapsed += step
    set_color(*original_color)

# -------------------------
# HTTP Request Handler
# -------------------------
async def handle_client(reader, writer):
    global current_task
    try:
        request_line = await reader.readline()
        while await reader.readline() != b"\r\n":
            pass

        method, url, _ = str(request_line, "utf-8").split()
        print(f"Received request: {method} {url}")

        response = ""
        content_type = "application/json"

        if method == "GET" and url == "/health":
            response = json.dumps({"status": "ok", "device_id": DEVICE_ID, "api": "1.0.0"})
        elif method == "GET" and url == "/sensor":
            response = json.dumps(read_light_sensor())
        elif method == "GET" and url == "/led":
            set_color(65535, 65535, 65535)
            await asyncio.sleep_ms(300)
            set_color(0, 0, 0)
            response = json.dumps({"blink": "done"})
        elif method == "POST" and url == "/tone":
            raw_data = await reader.read(1024)
            data = json.loads(raw_data)
            freq = int(data.get("freq", 0))
            duration = int(data.get("ms", 200))

            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)
            current_task = asyncio.create_task(play_tone(freq, duration))
            response = json.dumps({"playing": True, "until_ms_from_now": duration})
        elif method == "POST" and url == "/melody":
            raw_data = await reader.read(2048)
            data = json.loads(raw_data)
            notes = data.get("notes", [])
            gap_ms = int(data.get("gap_ms", 20))
            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)
            current_task = asyncio.create_task(play_melody(notes, gap_ms))
            response = json.dumps({"queued": len(notes)})
        elif method == "POST" and url == "/led":
            for _ in range(5):
                set_color(65535, 0, 0)
                await asyncio.sleep_ms(300)
                set_color(0, 0, 0)
                await asyncio.sleep_ms(300)
            response = json.dumps({"led_blink": "red 5 times"})
        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\n")
            await writer.drain()
            await writer.aclose()
            return

        writer.write(
            "HTTP/1.0 200 OK\r\nContent-Type: {}\r\n\r\n".format(content_type).encode()
        )
        writer.write(response.encode())
        await writer.drain()
        await writer.aclose()
        print("Request handled successfully")
    except Exception as e:
        print("Error handling request:", e)
        await writer.aclose()

# -------------------------
# Main Event Loop
# -------------------------
async def main():
    print("Starting web server...")
    await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("Server running on port 80...")
    while True:
        await asyncio.sleep(1)

# -------------------------
# Run Server
# -------------------------
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Stopping server...")
    stop_buzzer()
    set_color(0, 0, 0)
    red.deinit()
    green.deinit()
    blue.deinit()
