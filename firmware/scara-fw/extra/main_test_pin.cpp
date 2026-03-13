#include <Arduino.h>

const int pinsToTest[] = {
  9, 10, 11, 12, 13,     // common D pins
  A0, A1, A2, A3, A4, A5 // analog pins often used by CNC shield control
};

void setup() {
  Serial.begin(115200);
  delay(300);
  Serial.println("Pin monitor starting...");

  for (int p : pinsToTest) {
    pinMode(p, INPUT_PULLUP);
  }
}

void loop() {
  for (int p : pinsToTest) {
    int v = digitalRead(p);
    Serial.print(p);
    Serial.print("=");
    Serial.print(v);
    Serial.print("  ");
  }
  Serial.println();
  delay(200);
}