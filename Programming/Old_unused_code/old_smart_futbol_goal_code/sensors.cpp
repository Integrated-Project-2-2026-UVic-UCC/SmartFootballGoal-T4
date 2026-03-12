#include "sensors.h"
#include "score.h"
#include <Wire.h>
#include <VL53L1X.h>
VL53L1X sensor[NUM_SENSORS];
int sensorScoreMult[NUM_SENSORS] = { 5, 3, 1, 3, 5 };

int distance1 = 0;
int distance2 = 0;
int sensorIndex1 = -1;
int sensorIndex2 = -1;

bool firstDetected = false;
bool waitingSecond = false;
int detectedCount = 0;

unsigned long firstDetectTime = 0;

void startSensors() {
  Wire.begin();
  for (int i = 0; i < NUM_SENSORS; i++) {
    sensor[i].init();
    sensor[i].setDistanceMode(VL53L1X::Short);  //change this in different distances, for the moment short
    sensor[i].setMeasurementTimingBudget(50000);
    sensor[i].startContinuous(50);
    sensor[i].setROISize(4, 4);  //Measurament region of interest, the lowest posible = 4, highest = 16
  }
}

float readSensors() {

  for (int i = 0; i < NUM_SENSORS; i++) {

    int distance = sensor[i].readRangeContinuousMillimeters();

    if (abs(distance - STANDARD_DISTANCE) > TOLERANCE) {

      if (!firstDetected) {
        distance1 = distance;
        sensorIndex1 = i;
        firstDetected = true;
        waitingSecond = true;
        firstDetectTime = millis();
        Serial.print("Distance 1: ");
        Serial.println(distance1);
      }

      else if (waitingSecond && detectedCount < 2) {

        if (millis() - firstDetectTime >= WAIT_TIME) {
          distance2 = distance;
          sensorIndex2 = i;
          waitingSecond = false;
          detectedCount = 2;
          Serial.print("Distance 2: ");
          Serial.println(distance2);
        }
      }
    }
  }

  // If there is a goal, calculate score
  if (firstDetected) {
    float score = calculateScore();
    detectedCount = 0;
    firstDetected = false;

    Serial.print("Score: ");
    Serial.println(score);

    return score;  // send score to main
  } else {
    return 0;
  }
}
