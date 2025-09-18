from machine import Pin, PWM
import time

buzzer = PWM(Pin(18))
buzzer.freq(440)        # A4 note
buzzer.duty_u16(32768)  # 50% volume
time.sleep(1)           # play for 1 second
buzzer.duty_u16(0)      # stop
