#ifndef WEBSERVER_ESP32_H
#define WEBSERVER_ESP32_H

#include <WiFi.h>
#include <WebServer.h>

void inicialazeWebServer();
void updateScore(float newScore);
void handleWebServer();

#endif
