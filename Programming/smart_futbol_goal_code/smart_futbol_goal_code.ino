#include <Arduino.h>
#include "sensors.h"
#include "webserver_esp32.h"
float score = -1;
void setup() {
  Serial.begin(115200);
  startSensors();
  inicialazeWebServer();
}

void loop() {
  score = readSensors();  
  if (score > 0) {
    updateScore(score);
  }
  handleWebServer();
}
