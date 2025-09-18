# Title: Pico Light WebServer Demo
import machine
import network
import time
import uasyncio as asyncio

# --- Hardware Setup ---
photo_sensor = machine.ADC(28) #pin setup

# --- Wi-Fi Configuration ---
SSID = "BU Guest (unencrypted)"
PASSWORD = ""  # Open network

# --- Connect to Wi-Fi ---
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(SSID, PASSWORD)

print("Connecting to Wi-Fi...")
while not wlan.isconnected():
    time.sleep(1)
print("Connected! IP address:", wlan.ifconfig()[0])

# --- HTTP Request Handler ---
async def handle_client(reader, writer):
    request_line = await reader.readline()
    # Skip headers
    while await reader.readline() != b"\r\n":
        pass

    # Read light sensor value
    light_val = photo_sensor.read_u16()

    # Prepare a simple HTML response
    html = f"""
    <html>
        <head><title>Pico Light Demo</title></head>
        <body>
            <h1>Pico Light Sensor</h1>
            <p>Current light sensor reading: {light_val}</p>
        </body>
    </html>
    """

    writer.write("HTTP/1.0 200 OK\r\nContent-Type: text/html\r\n\r\n".encode())
    writer.write(html.encode())
    await writer.drain()
    await writer.aclose()

async def main():
    server = await asyncio.start_server(handle_client, "0.0.0.0", 80)
    print("Web server running on port 80...")
    # Keep the server alive indefinitely
    while True:
        await asyncio.sleep(1)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Server stopped.")

