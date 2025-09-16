import machine
import network
import time
import uasyncio as asyncio
import json
import ubinascii
    
# ---------------- CONFIG ----------------
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

# -------------------------

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

        # ---------------------
        # POST Endpoints
        # ---------------------
        elif method == "POST" and url == "/tone":
            raw_data = await reader.read(1024)
            data = json.loads(raw_data)
            freq = int(data.get("freq", 0))
            duration = int(data.get("ms", 200))
            duty = float(data.get("duty", 0.5))

            # Cancel currently playing tone/melody
            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)  # Small pause to ensure cancellation
            current_task = asyncio.create_task(play_tone(freq, duration, duty))

            response = json.dumps({"playing": True, "until_ms_from_now": duration})

        elif method == "POST" and url == "/melody":
            raw_data = await reader.read(2048)
            data = json.loads(raw_data)
            notes = data.get("notes", [])
            gap_ms = int(data.get("gap_ms", 20))

            # Cancel currently playing tone/melody
            if current_task:
                current_task.cancel()
                await asyncio.sleep_ms(10)
            current_task = asyncio.create_task(play_melody(notes, gap_ms))

            response = json.dumps({"queued": len(notes)})

        else:
            # Unknown endpoint
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
