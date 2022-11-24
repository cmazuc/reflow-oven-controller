all: compile upload

compile:
	arduino-cli --verbose compile --clean --fqbn arduino:avr:uno --libraries /home/chrismaz/arduino/Arduino/libraries reflow

upload:
	killall -9 picocom || true
	arduino-cli upload -p /dev/ttyACM0 --fqbn arduino:avr:uno reflow

NOW := $(shell date +%s)

connect:
	mv serial.log serial.log.$(NOW) || true
	picocom -b 9600 /dev/ttyACM0 --logfile serial.log

format:
	clang-format -style=Google -i reflow/*

clean:
	rm -fv serial.log*
