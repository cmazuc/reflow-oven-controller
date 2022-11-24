## Quick and dirty reflow oven controller

If you use this and burn down your house don't complain to me.

### reflow.ino

Arduino sketch which monitors a MAX31856 thermocouple and accepts commands over the serial port to turn on/off an oven. Circut design is well documented elsewhere and is straightforward.

### control.py

Attaches to the serial port and provides commands to the Arduino to follow a given profile. My oven takes about 25 seconds to react to changes, adjust lag_state accordingly for your oven. Most runs stay within 10 C of the target temperature during preheat/soak and within 3-5 C during reflow, ymmv.
