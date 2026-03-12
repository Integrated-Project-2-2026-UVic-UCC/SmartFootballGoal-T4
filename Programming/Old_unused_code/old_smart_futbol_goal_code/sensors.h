#ifndef SENSORS_H
#define SENSORS_H

#include <VL53L1X.h>

#define NUM_SENSORS 5
#define STANDARD_DISTANCE 900
#define TOLERANCE 20
#define WAIT_TIME 100

extern VL53L1X sensor[NUM_SENSORS];
extern int sensorScoreMult[NUM_SENSORS];

extern int distance1;
extern int distance2;
extern int sensorIndex1;
extern int sensorIndex2;

extern bool firstDetected;
extern bool waitingSecond;
extern int detectedCount;

extern unsigned long firstDetectTime;

void startSensors();
float readSensors();

#endif
