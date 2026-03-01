#include "webserver_esp32.h"
#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "ESP32";
const char* password = "12345678";

IPAddress local_ip(192, 168, 1, 1);
IPAddress gateway(192, 168, 1, 1);
IPAddress subnet(255, 255, 255, 0);

WebServer server(80);

// Última puntuación
float lastScore = 0;

// Historial de las últimas 5
float historial[5] = { 0, 0, 0, 0, 0 };

void updateScore(float newScore) {
  lastScore = newScore;

  // Desplazar historial
  for (int i = 4; i > 0; i--) {
    historial[i] = historial[i - 1];
  }
  historial[0] = newScore;
}
String createHTML() {
  String html = "<!DOCTYPE html><html><head>";
  html += "<meta name='viewport' content='width=device-width, initial-scale=1.0'>";
  html += "<style>";
  html += "body {font-family: Arial; text-align:center; background:#f2f2f2;}";
  html += ".titulo {font-size:40px; margin-top:40px;}";
  html += ".score {font-size:120px; font-weight:bold; color:#0077ff; margin:20px 0;}";
  html += ".subtitulo {font-size:22px; margin-top:40px;}";
  html += ".historial {font-size:26px; color:#444;}";
  html += "</style></head><body>";

  html += "<div class='titulo'>Last shoot score</div>";
  html += "<div class='score'>" + String(lastScore, 2) + "</div>";

  html += "<div class='subtitulo'>Last 5 shoots scores</div>";
  html += "<div class='historial'>";
  for (int i = 0; i < 5; i++) {
    html += String(historial[i], 2);
    if (i < 4) html += " • ";
  }
  html += "</div>";

  html += "</body></html>";
  return html;
}
void handle_OnConnect() {
  server.send(200, "text/html", createHTML());
}

void handle_NotFound() {
  server.send(404, "text/plain", "Not found");
}


void inicialazeWebServer() {
  WiFi.softAP(ssid, password);
  WiFi.softAPConfig(local_ip, gateway, subnet);

  server.on("/", handle_OnConnect);
  server.onNotFound(handle_NotFound);

  server.begin();
}

void handleWebServer() {
  server.handleClient();
}
