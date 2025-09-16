# CdS Photoresistor light measurement

The round component with two radial leads is a CdS photoresistor.
A key specification of a photoresistor is the resistance in darkness vs. bright light.

There is also a 10k ohm 1/8 watt resistor with axial leads provided.

A typical means of measuring light with a photoresistor using a microcontroller is to use the photoresistor as one resistor in a voltage divider circuit.
The voltage divider circuit center point is connected to an analog-to-digital converter (ADC) input of the microcontroller.
The ADC measures the voltage at the junction of the two resistors.
By calibrating the photoresistor measurement vs. a known intensity of light, the photoresistor voltage divider input to the ADC can be converted to a light level.

A voltage source is needed for the voltage divider circuit, which on the Pi Pico can be taken from the "3V3 OUT" pin.
