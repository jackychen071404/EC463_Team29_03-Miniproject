from machine import Pin
from utime import sleep

pin = Pin("LED", Pin.OUT)

print("LED starts flashing...")
while True:
    try:
        pin.toggle()    #Toggle the LED state (ON -> OFF, OFF -> ON)
        sleep(5) # sleep 1sec
    except KeyboardInterrupt:
        break
pin.off()
print("Finished.")
