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
# Helper Functions
# -------------------------
def stop_buzzer():
    """Stop the buzzer."""
    buzzer.duty_u16(0)
    print("Buzzer stopped")

async def play_tone(freq: int, duration_ms: int, duty: float = 0.5):
    """Play a single tone asynchronously."""
    if freq <= 0 or duration_ms <= 0:
        print("Skipping invalid tone")
        return

    print(f"Playing tone: {freq}Hz for {duration_ms}ms (duty={duty})")
    buzzer.freq(int(freq))
    buzzer.duty_u16(int(duty * 65535))
    await asyncio.sleep_ms(duration_ms)
    stop_buzzer()

async def play_melody(notes: list, gap_ms: int = 20):
    """Play a sequence of notes asynchronously."""
    print(f"Playing melody with {len(notes)} notes, gap={gap_ms}ms")
    for note in notes:
        freq = note.get("freq", 0)
        duration = note.get("ms", 200)
        await play_tone(freq, duration)
        await asyncio.sleep_ms(gap_ms)

def read_light_sensor():
    """Return photoresistor readings as raw, norm, and estimated lux."""
    raw = photo_sensor.read_u16()
    norm = raw / 65535
    lux_est = norm * 200
    return {"raw": raw, "norm": round(norm, 3), "lux_est": round(lux_est, 1)}

async def blink_led(r, g, b, duration_ms=500):
    """Blink LED once and restore previous color."""
    global current_color
    original_color = current_color
    set_color(r, g, b)  # Set blink color

    # Hold the color for the duration while yielding to asyncio
    elapsed = 0
    step = 50  # 50 ms steps
    while elapsed < duration_ms:
        await asyncio.sleep_ms(step)
        elapsed += step

    set_color(*original_color)  # Restore previous color

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
        print(f"Received request: {method} {url}")

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
            # Blink once (0.3s on, 0.3s off)
            set_color(65535, 65535, 65535)  # white for blink
            await asyncio.sleep_ms(300)
            set_color(0, 0, 0)  # off
            response = json.dumps({"blink": "done"})


        # ---------------------
        # POST Endpoints
        # ---------------------
        elif method == "POST" and url == "/tone":
            raw_data = await reader.read(1024)
            data = json.loads(raw_data)
            freq = int(data.get("freq", 0))
            duration = int(data.get("ms", 200))
            duty = float(data.get("duty", 0.5))

            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)
            current_task = asyncio.create_task(play_tone(freq, duration, duty))

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
                # Blink red 5 times
                for _ in range(5):
                    set_color(0, 65535, 0)  # red on
                    await asyncio.sleep_ms(300)
                    set_color(0, 0, 0)      # off
                    await asyncio.sleep_ms(300)

                response = json.dumps({"led_blink": "red 5 times"})
            except Exception as e:
                response = json.dumps({"error": str(e)})


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
    set_color(0, 0, 0)  # Turn off LED
    red.deinit()
    green.deinit()
    blue.deinit()
