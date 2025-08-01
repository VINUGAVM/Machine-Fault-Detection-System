#include <WiFi.h>
#include <HTTPClient.h>

const char* ssid = "arpu";
const char* password = "hello world";
const char* serverName = "http://192.168.118.164:5000/update"; // Replace with your server IP and port

const int sensorPin = 34; // GPIO pin connected to the sound sensor
int sensorValue = 0;

void setup() {
  Serial.begin(115200);
  WiFi.begin(ssid, password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(1000);
    Serial.println("Connecting to WiFi...");
  }

  Serial.println("Connected to WiFi");
}

void loop() {
  sensorValue = analogRead(sensorPin);
  Serial.print("Sensor Value: ");
  Serial.println(sensorValue);

  if (WiFi.status() == WL_CONNECTED) {
    HTTPClient http;
    String serverPath = String(serverName) + "?sensor=" + String(sensorValue);

    http.begin(serverPath.c_str());
    int httpResponseCode = http.GET();

    if (httpResponseCode > 0) {
      Serial.print("HTTP Response code: ");
      Serial.println(httpResponseCode);
    } else {
      Serial.print("Error code: ");
      Serial.println(httpResponseCode);
    }

    http.end();
  } else {
    Serial.println("WiFi Disconnected");
  }

  delay(100); // Send data every second
}
