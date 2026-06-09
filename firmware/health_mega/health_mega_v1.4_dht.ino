/*
 * OceanPulse Health Mega Firmware v1.4 (DHT Edition)
 * SPEC-002 Compliant - Health Circuit
 *
 * Pin 2: Main Reset Relay
 * Pin 4: DHT Sensor (Data Pin)
 */

#include <DHT.h>

#define DHTPIN 4
#define DHTTYPE DHT22 // Change to DHT11 if using blue one
#define RELAY_PIN 2

DHT dht(DHTPIN, DHTTYPE);
String inputBuffer = "";

void setup() {
  Serial.begin(115200);
  dht.begin();
  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);
  Serial.println("READY:HEALTH_MEGA:v1.4_DHT");
}

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();
  if (cmd == "STATUS") {
    float h = dht.readHumidity();
    float t = dht.readTemperature();
    Serial.print("STATUS:OK:RELAY=OFF,TEMP=");
    if (isnan(t)) Serial.print("ERR"); else Serial.print(t, 1);
    Serial.print(",HUM=");
    if (isnan(h)) Serial.println("ERR"); else { Serial.print(h, 1); Serial.println("%"); }
  } else if (cmd == "PING") {
    Serial.println("PONG");
  }
}

void loop() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n' || c == '\r') {
      if (inputBuffer.length() > 0) {
        processCommand(inputBuffer);
        inputBuffer = "";
      }
    } else {
      inputBuffer += c;
    }
  }
}
