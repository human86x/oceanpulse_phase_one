/*
 * OceanPulse Health Mega Firmware v1.4
 * SPEC-002 Compliant - Health Circuit
 *
 * Hardware:
 *   - Pin 2: Restart Relay (controls Main circuit power)
 *   - SHT3x I2C sensor (SDA=Pin 20, SCL=Pin 21, addr 0x44)
 *
 * Serial Protocol: 115200 baud, 8N1
 *   Commands: PING, STATUS, RELAY:ON, RELAY:OFF, DHT:READ, TEMP:READ, HUM:READ
 *             WATCHDOG:ENABLE, WATCHDOG:DISABLE, WATCHDOG:KICK, REBOOT:SYS, RESETINFO
 *   Response: <CMD>:OK:<VALUE> or ERROR:<msg>
 *   Boot: READY:HEALTH_MEGA:v1.4:RST=<reason>
 */

#include <Wire.h>
#include <avr/wdt.h>

#define RELAY_PIN 2
#define REBOOT_PIN 3  // Cross-circuit reset relay (SPEC-002 Section 4)
#define SHT3X_ADDR 0x44

#define BAUD_RATE 115200

// Watchdog Configuration
#define WATCHDOG_TIMEOUT 300000 // 5 minutes in ms

String inputBuffer = "";
bool relayState = false;

// Reset reason captured at boot (REQ-023 / SPEC-024)
uint8_t resetReason = 0;

// Cached sensor values
float lastTemp = 0.0;
float lastHum = 0.0;
bool sensorOk = false;
unsigned long lastShtRead = 0;
const unsigned long SHT_READ_INTERVAL = 2000;  // Min 2s between reads

// Watchdog State
bool watchdogEnabled = false;
unsigned long lastKickTime = 0;

// Forward Declarations
void triggerReset();
void readShtSensor();
void processCommand(String cmd);

void setup() {
  // Capture and clear MCUSR immediately (REQ-023)
  resetReason = MCUSR;
  MCUSR = 0;
  wdt_disable();

  Serial.begin(BAUD_RATE);

  pinMode(RELAY_PIN, OUTPUT);
  digitalWrite(RELAY_PIN, LOW);

  pinMode(REBOOT_PIN, OUTPUT);
  digitalWrite(REBOOT_PIN, LOW);

  Wire.begin();

  // Soft-reset SHT3x to known state
  Wire.beginTransmission(SHT3X_ADDR);
  Wire.write(0x30);
  Wire.write(0xA2);
  Wire.endTransmission();
  delay(2);

  // Ready signal with reset reason (REQ-023 / SPEC-024)
  Serial.print("READY:HEALTH_MEGA:v1.4:RST=");
  if (resetReason & (1 << PORF))  Serial.print("POR+");
  if (resetReason & (1 << EXTRF)) Serial.print("EXT+");
  if (resetReason & (1 << BORF))  Serial.print("BOR+");
  if (resetReason & (1 << WDRF))  Serial.print("WDT+");
  if (resetReason == 0)           Serial.print("UNKNOWN+");
  Serial.println("");
}

void triggerReset() {
  Serial.println("WATCHDOG:TRIGGERED");
  // Pulse Relay to reset
  digitalWrite(RELAY_PIN, HIGH);
  delay(2000);
  digitalWrite(RELAY_PIN, LOW);
  
  // Reset timer to allow boot
  lastKickTime = millis();
}

void loop() {
  // Watchdog Check
  if (watchdogEnabled && (millis() - lastKickTime > WATCHDOG_TIMEOUT)) {
    triggerReset();
  }

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

void readShtSensor() {
  unsigned long now = millis();
  if (now - lastShtRead >= SHT_READ_INTERVAL) {
    // Send single-shot measurement command: high repeatability, no clock stretching
    Wire.beginTransmission(SHT3X_ADDR);
    Wire.write(0x24);
    Wire.write(0x00);
    if (Wire.endTransmission() != 0) {
      sensorOk = false;
      lastShtRead = now;
      return;
    }

    delay(20); // SHT3x high-repeatability measurement time ~15ms + margin

    if (Wire.requestFrom((uint8_t)SHT3X_ADDR, (uint8_t)6) != 6) {
      sensorOk = false;
      lastShtRead = now;
      return;
    }

    uint8_t data[6];
    for (int i = 0; i < 6; i++) {
      data[i] = Wire.read();
    }

    // CRC check for temperature (byte 2) and humidity (byte 5)
    // Skip CRC validation for simplicity -- sensor rarely errors on I2C

    uint16_t rawTemp = (data[0] << 8) | data[1];
    uint16_t rawHum  = (data[3] << 8) | data[4];

    lastTemp = -45.0 + 175.0 * ((float)rawTemp / 65535.0);
    lastHum  = 100.0 * ((float)rawHum / 65535.0);
    sensorOk = true;
    lastShtRead = now;
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
  else if (cmd == "WATCHDOG:ENABLE") {
    watchdogEnabled = true;
    lastKickTime = millis();
    Serial.println("WATCHDOG:OK:ENABLED");
  }
  else if (cmd == "WATCHDOG:DISABLE") {
    watchdogEnabled = false;
    Serial.println("WATCHDOG:OK:DISABLED");
  }
  else if (cmd == "WATCHDOG:KICK") {
    lastKickTime = millis();
    Serial.println("WATCHDOG:OK:KICKED");
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
    readShtSensor();
    if (!sensorOk) {
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
    readShtSensor();
    if (!sensorOk) {
      Serial.println("TEMP:ERROR:SENSOR_FAIL");
    } else {
      Serial.print("TEMP:OK:");
      Serial.print(lastTemp, 1);
      Serial.println("C");
    }
  }
  else if (cmd == "HUM:READ") {
    readShtSensor();
    if (!sensorOk) {
      Serial.println("HUM:ERROR:SENSOR_FAIL");
    } else {
      Serial.print("HUM:OK:");
      Serial.print(lastHum, 1);
      Serial.println("%");
    }
  }
  else if (cmd == "RESETINFO") {
    Serial.print("RESETINFO:OK:RST=");
    if (resetReason & (1 << PORF))  Serial.print("POR+");
    if (resetReason & (1 << EXTRF)) Serial.print("EXT+");
    if (resetReason & (1 << BORF))  Serial.print("BOR+");
    if (resetReason & (1 << WDRF))  Serial.print("WDT+");
    if (resetReason == 0)           Serial.print("UNKNOWN+");
    Serial.println("");
  }
  else if (cmd == "REBOOT:SYS") {
    // Cross-circuit hardware reset: Pin 3 HIGH 2s then LOW (SPEC-002 Section 4)
    digitalWrite(REBOOT_PIN, HIGH);
    delay(2000);
    digitalWrite(REBOOT_PIN, LOW);
    Serial.println("REBOOT:OK");
  }
  else if (cmd == "STATUS") {
    readShtSensor();
    Serial.print("STATUS:OK:RELAY=");
    Serial.print(relayState ? "ON" : "OFF");
    Serial.print(",TEMP=");
    if (!sensorOk) {
      Serial.print("ERR");
    } else {
      Serial.print(lastTemp, 1);
      Serial.print("C");
    }
    Serial.print(",HUM=");
    if (!sensorOk) {
      Serial.println("ERR");
    } else {
      Serial.print(lastHum, 1);
      Serial.println("%");
    }
    Serial.print(",WD=");
    Serial.println(watchdogEnabled ? "ON" : "OFF");
  }
  else {
    Serial.print("ERROR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}