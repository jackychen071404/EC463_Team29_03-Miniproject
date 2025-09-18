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
    """Set RGB color and save state."""
    global current_color
    current_color = (r, g, b)
    red.duty_u16(r)
    green.duty_u16(g)
    blue.duty_u16(b)
    print(f"[LED] Set color -> R:{r} G:{g} B:{b}")

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
# Async Task Tracking
# -------------------------
current_task = None  # Will store the currently playing tone/melody

# -------------------------
# Helper Functions
# -------------------------
def stop_buzzer():
    """Stop the buzzer."""
    buzzer.duty_u16(0)
    print("[Buzzer] Stopped")

def read_light_sensor():
    """Return photoresistor readings as raw, normalized, and estimated lux."""
    raw = photo_sensor.read_u16()
    norm = raw / 65535
    lux_est = norm * 200
    return {"raw": raw, "norm": round(norm, 3), "lux_est": round(lux_est, 1)}

def get_volume_from_light(min_duty=0.1, max_duty=0.8):
    """Map the current light level to a PWM duty cycle (original function for API compatibility)."""
    norm = read_light_sensor()["norm"]
    return int((min_duty + (max_duty - min_duty) * norm) * 65535)

def get_volume_from_light_stepped(min_duty=0.1, max_duty=0.8, step=0.05):
    """Map current light to PWM duty in discrete steps (default 5%)."""
    norm = read_light_sensor()["norm"]
    raw_duty = min_duty + (max_duty - min_duty) * norm
    quantized_duty = step * int(raw_duty / step)
    return int(quantized_duty * 65535)

# -------------------------
# Tone / Melody Functions
# -------------------------
async def play_tone(freq, duration_ms, duty_override=None):
    """
    Play a tone asynchronously with real-time stepped volume scaling based on light.
    If duty_override is provided (0.0–1.0), use it instead.
    """
    if freq <= 0 or duration_ms <= 0:
        print("[Tone] Skipping invalid tone")
        return

    buzzer.freq(int(freq))
    step_ms = 50
    elapsed = 0
    while elapsed < duration_ms:
        if duty_override is not None:
            duty_val = int(duty_override * 65535)
        else:
            duty_val = get_volume_from_light_stepped()
        buzzer.duty_u16(duty_val)
        print(f"[Tone] Freq: {freq}Hz, Time: {elapsed}/{duration_ms}ms, Duty: {duty_val/65535:.2f}")
        await asyncio.sleep_ms(step_ms)
        elapsed += step_ms
    buzzer.duty_u16(0)
    print(f"[Tone] Finished {freq}Hz")

async def play_melody(notes, gap_ms=20):
    """
    Play a sequence of notes asynchronously.
    Each note is a dictionary with keys 'freq', 'ms', and optional 'duty'.
    """
    print(f"[Melody] Starting melody with {len(notes)} notes, gap {gap_ms}ms")
    for i, note in enumerate(notes, start=1):
        freq = note.get("freq", 0)
        duration = note.get("ms", 200)
        duty = note.get("duty", None)
        print(f"[Melody] Note {i}/{len(notes)}: {freq}Hz for {duration}ms")
        await play_tone(freq, duration, duty_override=duty)
        await asyncio.sleep_ms(gap_ms)
    print("[Melody] Finished melody")

async def blink_led(r, g, b, duration_ms=500):
    """Blink LED once and restore previous color."""
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
        while await reader.readline() != b"\r\n":  # Skip headers
            pass

        method, url, _ = str(request_line, "utf-8").split()
        print(f"[HTTP] {method} {url}")

        response = ""
        content_type = "application/json"

        # ---------------------
        # GET Endpoints
        # ---------------------
        if method == "GET" and url == "/health":
            response = json.dumps({"status": "ok", "device_id": DEVICE_ID, "api": "1.0.0"})

        elif method == "GET" and url == "/sensor":
            response = json.dumps(read_light_sensor())

        elif method == "GET" and url == "/led":
            await blink_led(65535, 65535, 65535, duration_ms=300)
            response = json.dumps({"blink": "done"})

        # ---------------------
        # POST Endpoints
        # ---------------------
        elif method == "POST" and url == "/tone":
            raw_data = await reader.read(1024)
            data = json.loads(raw_data)
            freq = int(data.get("freq", 0))
            duration = int(data.get("ms", 200))
            duty = data.get("duty", None)

            # Cancel any current task
            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)

            # Use duty override if provided
            duty_override = float(duty) if duty is not None else None
            current_task = asyncio.create_task(play_tone(freq, duration, duty_override))

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
            try:
                for _ in range(5):
                    set_color(65535, 0, 0)  # red
                    await asyncio.sleep_ms(300)
                    set_color(0, 0, 0)
                    await asyncio.sleep_ms(300)
                response = json.dumps({"led_blink": "red 5 times"})
            except Exception as e:
                response = json.dumps({"error": str(e)})

        else:
            writer.write(b"HTTP/1.0 404 Not Found\r\n\r\n")
            await writer.drain()
            await writer.aclose()
            return

        # Send response
        writer.write(
            "HTTP/1.0 200 OK\r\nContent-Type: {}\r\n\r\n".format(content_type).encode()
        )
        writer.write(response.encode())
        await writer.drain()
        await writer.aclose()
        print("[HTTP] Request handled successfully")

    except Exception as e:
        print("[HTTP] Error:", e)
        await writer.aclose()

# -------------------------
# Main Event Loop
# -------------------------
async def main():
    print("[Server] Starting web server...")
    await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print(f"[Server] Running on port 80, IP {IP_ADDRESS}")
    while True:
        await asyncio.sleep(1)

# -------------------------
# Run Server
# -------------------------
try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("[Server] Stopping...")
    stop_buzzer()
    set_color(0, 0, 0)
    red.deinit()
    green.deinit()
    blue.deinit()
