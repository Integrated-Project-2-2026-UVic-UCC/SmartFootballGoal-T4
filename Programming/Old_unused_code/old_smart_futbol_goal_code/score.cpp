#include "score.h"
#include "sensors.h"


float calculateScore() {

  float tx = abs(distance1 - 450.0) * sensorScoreMult[sensorIndex1];
  float t;

  if (waitingSecond) {
    t = tx / 450.0;
  } else {
    float ty = abs(distance2 - 450.0) * sensorScoreMult[sensorIndex2];
    t = (tx + ty) / 900.0;
  }

  return t * t;
}
