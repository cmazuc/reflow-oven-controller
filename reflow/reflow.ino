#include <Adafruit_MAX31856.h>
#include <Arduino.h>

enum pins {
  // 1
  // 2
  // 3
  OVEN = 4,
  // 5
  // 6
  MAX_DATA_READY = 7, // DRDY
  MAX_FAULT = 8, // FLT
  MAX_CHIP_SELECT = 9, // CS
  MAX_DATA_IN = 10, // SDI
  MAX_DATA_OUT = 11, // SDO
  MAX_CLOCK = 12 // SCK
  // 13
};

const uint8_t enable_command = 101; // e

const uint8_t tick_ms = 250;
volatile bool oven_on = false;
volatile int16_t temperature = 0;
volatile int16_t fault = 0;

Adafruit_MAX31856 MAX31856 =
    Adafruit_MAX31856(MAX_CHIP_SELECT, MAX_DATA_IN, MAX_DATA_OUT, MAX_CLOCK);

void setup() {
  pinMode(MAX_DATA_READY, INPUT);
  pinMode(MAX_FAULT, INPUT);

  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);

  pinMode(OVEN, OUTPUT);
  digitalWrite(OVEN, LOW);

  MAX31856.begin();
  MAX31856.setThermocoupleType(MAX31856_TCTYPE_K);

  Serial.begin(9600);
}

volatile uint32_t loop_start = 0;
volatile uint32_t wait_time = 0;
volatile char output[64];

void loop() {
  loop_start = millis();

  temperature = MAX31856.readThermocoupleTemperature();
  fault = MAX31856.readFault();

  if (Serial.available()) {
    oven_on = Serial.read() == enable_command ? true : false;
  }

  if (oven_on) {
    digitalWrite(OVEN, HIGH);
  } else {
    digitalWrite(OVEN, LOW);
  }

  snprintf(output, sizeof(output), "{\"t\": %d, \"f\": %d, \"s\": %d, \"w\": %d}\r\n", temperature, fault, oven_on, wait_time);

  for (int i = 0; i < strlen(output); i++) {
    Serial.print(char(output[i]));
  }

  wait_time = wait_time > tick_ms ? 0 : tick_ms - (millis() - loop_start);
  delay(wait_time);
}
