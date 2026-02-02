/*
 * OceanPulse Health Mega Firmware v1.1
 * SPEC-002 Compliant - Health Circuit
 *
 * Hardware:
 *   - Pin 2: Restart Relay (controls Main circuit power)
 *   - Pin 3: DHT11/DHT22 Data (temp/humidity sensor)
 *
 * Serial Protocol: 115200 baud, 8N1
 *   Commands: PING, STATUS, RELAY:ON, RELAY:OFF, DHT:READ, TEMP:READ, HUM:READ
 *   Response: <CMD>:OK:<VALUE> or ERROR:<msg>
 */

#include <DHT.h>

#define RELAY_PIN 2
#define DHT_PIN 3
#define DHT_TYPE DHT22  // Trying DHT22 mode

#define BAUD_RATE 115200

DHT dht(DHT_PIN, DHT_TYPE);

String inputBuffer = "";
bool relayState = false;

// Cached sensor values
float lastTemp = NAN;
float lastHum = NAN;
unsigned long lastDhtRead = 0;
const unsigned long DHT_READ_INTERVAL = 2000;  // Min 2s between reads

void setup() {
  Serial.begin(BAUD_RATE);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  dht.begin();

  Serial.println("READY:HEALTH_MEGA:v1.1");
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
      if (inputBuffer.length() > 64) {
        inputBuffer = "";
        Serial.println("ERROR:BUFFER_OVERFLOW");
      }
    }
  }
}

void readDhtSensor() {
  unsigned long now = millis();
  if (now - lastDhtRead >= DHT_READ_INTERVAL) {
    lastHum = dht.readHumidity();
    lastTemp = dht.readTemperature();
    lastDhtRead = now;
  }
}

void processCommand(String cmd) {
  cmd.trim();
  cmd.toUpperCase();

  if (cmd == "PING") {
    Serial.println("PING:OK:ALIVE");
  }
  else if (cmd == "UPTIME") {
    Serial.print("UPTIME:OK:");
    Serial.println(millis());
  }
  else if (cmd == "RELAY:ON") {
    digitalWrite(RELAY_PIN, HIGH);
    relayState = true;
    Serial.println("RELAY:OK:ON");
  }
  else if (cmd == "RELAY:OFF") {
    digitalWrite(RELAY_PIN, LOW);
    relayState = false;
    Serial.println("RELAY:OK:OFF");
  }
  else if (cmd == "RELAY:STATUS") {
    Serial.print("RELAY:OK:");
    Serial.println(relayState ? "ON" : "OFF");
  }
  else if (cmd == "DHT:READ") {
    readDhtSensor();
    if (isnan(lastTemp) || isnan(lastHum)) {
      Serial.println("DHT:ERROR:SENSOR_FAIL");
    } else {
      Serial.print("DHT:OK:T=");
      Serial.print(lastTemp, 1);
      Serial.print("C,H=");
      Serial.print(lastHum, 1);
      Serial.println("%");
    }
  }
  else if (cmd == "TEMP:READ") {
    readDhtSensor();
    if (isnan(lastTemp)) {
      Serial.println("TEMP:ERROR:SENSOR_FAIL");
    } else {
      Serial.print("TEMP:OK:");
      Serial.print(lastTemp, 1);
      Serial.println("C");
    }
  }
  else if (cmd == "HUM:READ") {
    readDhtSensor();
    if (isnan(lastHum)) {
      Serial.println("HUM:ERROR:SENSOR_FAIL");
    } else {
      Serial.print("HUM:OK:");
      Serial.print(lastHum, 1);
      Serial.println("%");
    }
  }
  else if (cmd == "STATUS") {
    readDhtSensor();
    Serial.print("STATUS:OK:RELAY=");
    Serial.print(relayState ? "ON" : "OFF");
    Serial.print(",TEMP=");
    if (isnan(lastTemp)) {
      Serial.print("ERR");
    } else {
      Serial.print(lastTemp, 1);
      Serial.print("C");
    }
    Serial.print(",HUM=");
    if (isnan(lastHum)) {
      Serial.println("ERR");
    } else {
      Serial.print(lastHum, 1);
      Serial.println("%");
    }
  }
  else {
    Serial.print("ERROR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}
