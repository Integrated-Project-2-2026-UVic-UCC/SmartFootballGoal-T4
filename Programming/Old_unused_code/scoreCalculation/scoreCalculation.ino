/*
  IMPORTANT:
  - All sensors have the same default I2C address.
  - MUST use the XSHUT pins to power them one by one
    and assign a different I2C address to each sensor.
*/

#include <Wire.h>
#include <VL53L0X.h>   // Replace with your actual library

#define NUM_SENSORS 5
#define STANDARD_DISTANCE 900      // 90 cm in mm
#define TOLERANCE 20               // mm tolerance
#define WAIT_TIME 100              // ms

VL53L0X sensor[NUM_SENSORS];
int sensorScoreMult[NUM_SENSORS] = {5,3,1,3,5};

int detectedCount = 0;

int distance1 = 0;
int distance2 = 0;
int sensorIndex1 = -1;
int sensorIndex2 = -1;
bool firstDetected = false;
bool waitingSecond = false;

unsigned long firstDetectTime = 0;

float score = 0;

void setup() {
  Serial.begin(115200);
  Wire.begin();

  for (int i = 0; i < NUM_SENSORS; i++) {
    sensor[i].init();
    sensor[i].startContinuous();
  }
}

void loop() {

  for (int i = 0; i < NUM_SENSORS; i++) {

    int distance = sensor[i].readRangeContinuousMillimeters();

    // Check with tolerance instead of exact comparison
    if (abs(distance - STANDARD_DISTANCE) > TOLERANCE) {

      if (!firstDetected) {
        distance1 = distance;
        firstDetected = true;
        waitingSecond = true;
        sensorIndex1 = i;
        firstDetectTime = millis();
        Serial.print("Distance 1: ");
        Serial.println(distance1);
      }

      else if (waitingSecond && detectedCount < 2) {

        // Non-blocking wait time
        if (millis() - firstDetectTime >= WAIT_TIME) {
          distance2 = distance;
          waitingSecond = false;
          detectedCount = 2;
          sensorIndex2 = i;
          Serial.print("Distance 2: ");
          Serial.println(distance2);
        }
      }
    }
  }
  
  // Waiting time in order to not overburden the system
  if (firstDetected) {
    score = calculateScore(); // The score is calculed
    // Ready for next detection cycle
    detectedCount = 0;
    firstDetected = false;
    Serial.println(score);
  }
}
float calculateScore(){
  int x = distance1;
  float tx = abs(x - 450.0)* sensorScoreMult[sensorIndex1];
  if (waitingSecond){
    float t = tx/450;
  } else{
    int y = distance2;
    float ty abs(y-450.0)*sensorScoreMult[sensorIndex2];
    float t =  (tx + ty) / 900;
  }
  
  return t * t;

}