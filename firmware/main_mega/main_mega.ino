/*
 * OceanPulse Main Mega Firmware v1.4
 * SPEC-002 Compliant - Component Integration & Serial Protocol
 *
 * Serial Protocol:
 *   Baud: 115200, 8N1
 *   Commands: PING, TDS:READ, TDS:RAW, RELAY:ON, RELAY:OFF, TEMP:SET:<value>
 *             WATCHDOG:ENABLE, WATCHDOG:DISABLE, WATCHDOG:KICK, REBOOT:SYS, RESETINFO
 *   Response: <CMD>:OK:<VALUE>\n or ERROR:<msg>\n
 *   Boot: READY:MAIN_MEGA:v1.4:RST=<reason>
 * 
 * TDS Sensor: DFRobot Gravity TDS Meter (3.3V power)
 */

#include <avr/wdt.h>

#define RELAY_PIN 2
#define REBOOT_PIN 3  // Cross-circuit reset relay (SPEC-002 Section 4)
#define TDS_PIN A0
#define BAUD_RATE 115200

// TDS Sensor Configuration (DFRobot Gravity)
#define TDS_VREF 3.3          // Sensor powered at 3.3V
#define TDS_ADC_RANGE 1024.0  // 10-bit ADC
#define TDS_SAMPLES 10        // Average multiple readings

// Watchdog Configuration
#define WATCHDOG_TIMEOUT 300000 // 5 minutes in ms

String inputBuffer = "";
bool relayState = false;
float waterTemperature = 25.0;  // Default temp for compensation (Celsius)

// Reset reason captured at boot (REQ-023 / SPEC-024)
uint8_t resetReason = 0;

// Watchdog State
bool watchdogEnabled = false;
unsigned long lastKickTime = 0;

// Forward Declarations
void triggerReset();
int readTdsRaw();
float calculateTds(int rawValue);
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

  pinMode(TDS_PIN, INPUT);

  // Ready signal with reset reason (REQ-023 / SPEC-024)
  Serial.print("READY:MAIN_MEGA:v1.4:RST=");
  if (resetReason & (1 << PORF))  Serial.print("POR+");
  if (resetReason & (1 << EXTRF)) Serial.print("EXT+");
  if (resetReason & (1 << BORF))  Serial.print("BOR+");
  if (resetReason & (1 << WDRF))  Serial.print("WDT+");
  if (resetReason == 0)           Serial.print("UNKNOWN+");
  Serial.println("");
}

void triggerReset() {
  Serial.println("WATCHDOG:TRIGGERED");
  // Pulse Relay to reset (High = Active/Cut Power)
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

// Read TDS with averaging
int readTdsRaw() {
  long sum = 0;
  for (int i = 0; i < TDS_SAMPLES; i++) {
    sum += analogRead(TDS_PIN);
    delay(1);
  }
  return sum / TDS_SAMPLES;
}

// Convert raw ADC to TDS (ppm) using DFRobot formula
float calculateTds(int rawValue) {
  // Convert to voltage (sensor max output = 3.3V, but ADC ref is 5V)
  float voltage = rawValue * 5.0 / TDS_ADC_RANGE;

  // Clamp voltage to sensor range
  if (voltage > TDS_VREF) voltage = TDS_VREF;

  // Temperature compensation coefficient
  float compensationCoeff = 1.0 + 0.02 * (waterTemperature - 25.0);
  float compensationVoltage = voltage / compensationCoeff;

  // DFRobot TDS conversion formula (polynomial fit)
  float tdsValue = (133.42 * compensationVoltage * compensationVoltage * compensationVoltage
                  - 255.86 * compensationVoltage * compensationVoltage
                  + 857.39 * compensationVoltage) * 0.5;

  if (tdsValue < 0) tdsValue = 0;

  return tdsValue;
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
  else if (cmd == "TDS:READ") {
    int rawValue = readTdsRaw();
    float tds = calculateTds(rawValue);
    Serial.print("TDS:OK:");
    Serial.print(tds, 1);
    Serial.println(" ppm");
  }
  else if (cmd == "TDS:RAW") {
    int rawValue = readTdsRaw();
    float voltage = rawValue * 5.0 / TDS_ADC_RANGE;
    Serial.print("TDS:RAW:");
    Serial.print(rawValue);
    Serial.print(",V:");
    Serial.println(voltage, 3);
  }
  else if (cmd.startsWith("TEMP:SET:")) {
    float temp = cmd.substring(9).toFloat();
    if (temp >= 0 && temp <= 50) {
      waterTemperature = temp;
      Serial.print("TEMP:OK:");
      Serial.println(waterTemperature, 1);
    } else {
      Serial.println("ERROR:TEMP_OUT_OF_RANGE");
    }
  }
  else if (cmd == "TEMP:GET") {
    Serial.print("TEMP:OK:");
    Serial.println(waterTemperature, 1);
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
  else if (cmd == "REBOOT:SYS") {
    // Cross-circuit hardware reset: Pin 3 HIGH 2s then LOW (SPEC-002 Section 4)
    digitalWrite(REBOOT_PIN, HIGH);
    delay(2000);
    digitalWrite(REBOOT_PIN, LOW);
    Serial.println("REBOOT:OK");
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
  else if (cmd == "STATUS") {
    int rawTds = readTdsRaw();
    float tds = calculateTds(rawTds);
    Serial.print("STATUS:OK:RELAY=");
    Serial.print(relayState ? "ON" : "OFF");
    Serial.print(",TDS=");
    Serial.print(tds, 1);
    Serial.print("ppm,TEMP=");
    Serial.print(waterTemperature, 1);
    Serial.print("C,WD=");
    Serial.println(watchdogEnabled ? "ON" : "OFF");
  }
  else {
    Serial.print("ERROR:UNKNOWN_CMD:");
    Serial.println(cmd);
  }
}
