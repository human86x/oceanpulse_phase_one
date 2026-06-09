/*
 * OceanPulse Health Mega Firmware v2.2
 * SPEC-006 Compliant - Internal Health Monitoring (3x DHT11 + SHT3x)
 *
 * v2.2 vs v2.1:
 *   - Flattened STATUS format: SHT_T, SHT_H, DHT1_T, DHT1_H, etc. (No nested commas)
 *   - Added Wire.setWireTimeout(25000, true) to prevent I2C hangs (as per SPEC-011 audit)
 *   - Unified units (stripped C/%/V suffixes from STATUS for parsing clarity)
 *
 * Hardware:
 *   - Pin 2: Cross-circuit reboot relay (controls Main circuit power)
 *   - SHT3x I2C sensor (SDA=Pin 20, SCL=Pin 21, addr 0x44)
 *   - Pin 3: DHT11 #1 (Upper Shelf)
 *   - Pin 4: DHT11 #2 (Lower Shelf)
 *   - Pin 5: DHT11 #3 (Electrical Box)
 *   - A1: Battery Voltage (REQ-045 / SPEC-027)
 *
 * Serial Protocol: 115200 baud, 8N1
 */

#include <Wire.h>
#include <avr/wdt.h>

// --- Constants & Pins ---
#define BAUD_RATE 115200
#define RELAY_PIN 2             // legacy cross-reboot pin (kept for backward compat)
#define HARD_REBOOT_PIN 38      // cross-circuit hard-reboot relay (cuts Main Pi power).
                                // Active-HIGH (inverted 2026-05-30): idle LOW, pulse HIGH for 2s
                                // to engage. Paired with 2kOhm pull-down on IN -> GND on the
                                // relay-board so that when this Mega is unpowered (D38 floats)
                                // the pull-down keeps IN LOW and the other Pi stays powered.
                                // Cascade-safe: no Mega outage can cut the other circuit.
#define BATT_PIN A1
#define SHT3X_ADDR 0x44

#define DHT1_PIN 3
#define DHT2_PIN 4
#define DHT3_PIN 5
#define DHT4_PIN 6

// --- Sensor Abstraction Layer (SAL) ---

class Sensor {
public:
    virtual void begin() = 0;
    virtual void update() = 0;
    virtual String read() = 0;
    virtual String status() = 0;
    virtual bool ok() = 0;
};

class ShtSensor : public Sensor {
private:
    float _temp = 0.0;
    float _hum = 0.0;
    bool _ok = false;
    unsigned long _lastRead = 0;

public:
    void begin() override {
        Wire.begin();
        Wire.setWireTimeout(25000, true); // Prevent I2C hangs
        // Soft-reset SHT3x
        Wire.beginTransmission(SHT3X_ADDR);
        Wire.write(0x30);
        Wire.write(0xA2);
        Wire.endTransmission();
        delay(2);
    }

    void update() override {
        unsigned long now = millis();
        if (now - _lastRead < 2000 && _lastRead != 0) return;

        Wire.beginTransmission(SHT3X_ADDR);
        Wire.write(0x24);
        Wire.write(0x00);
        if (Wire.endTransmission() != 0) {
            _ok = false;
            _lastRead = now;
            return;
        }

        delay(20);

        if (Wire.requestFrom((uint8_t)SHT3X_ADDR, (uint8_t)6) != 6) {
            _ok = false;
            _lastRead = now;
            return;
        }

        uint8_t data[6];
        for (int i = 0; i < 6; i++) data[i] = Wire.read();

        uint16_t rawTemp = (data[0] << 8) | data[1];
        uint16_t rawHum  = (data[3] << 8) | data[4];

        _temp = -45.0 + 175.0 * ((float)rawTemp / 65535.0);
        _hum  = 100.0 * ((float)rawHum / 65535.0);
        _ok = true;
        _lastRead = now;
    }

    float temp() { return _temp; }
    float hum() { return _hum; }
    bool ok() override { return _ok; }

    String read() override {
        if (!_ok) return "ERROR";
        return "T=" + String(_temp, 1) + ",H=" + String(_hum, 1);
    }

    String status() override {
        return _ok ? "ALIVE" : "ERROR:SENSOR_FAIL";
    }
};

class Dht11Sensor : public Sensor {
private:
    uint8_t _pin;
    float _temp = 0.0;
    float _hum = 0.0;
    bool _ok = false;
    unsigned long _lastRead = 0;

public:
    Dht11Sensor(uint8_t pin) : _pin(pin) {}

    void begin() override {
        pinMode(_pin, INPUT_PULLUP);
    }

    void update() override {
        unsigned long now = millis();
        if (now - _lastRead < 2500 && _lastRead != 0) return; // DHT11 needs time

        uint8_t data[5] = {0, 0, 0, 0, 0};

        // Start Signal
        pinMode(_pin, OUTPUT);
        digitalWrite(_pin, LOW);
        delay(18);
        digitalWrite(_pin, HIGH);
        delayMicroseconds(40);
        pinMode(_pin, INPUT_PULLUP);

        // Wait for response
        unsigned long timeout = micros();
        while (digitalRead(_pin) == HIGH) if (micros() - timeout > 100) { _ok = false; _lastRead = now; return; }
        while (digitalRead(_pin) == LOW)  if (micros() - timeout > 200) { _ok = false; _lastRead = now; return; }
        while (digitalRead(_pin) == HIGH) if (micros() - timeout > 300) { _ok = false; _lastRead = now; return; }

        // Read 40 bits
        for (int i = 0; i < 40; i++) {
            while (digitalRead(_pin) == LOW);
            unsigned long start = micros();
            while (digitalRead(_pin) == HIGH);
            if (micros() - start > 40) {
                data[i/8] |= (1 << (7 - (i%8)));
            }
        }

        // Checksum
        if (data[4] == ((data[0] + data[1] + data[2] + data[3]) & 0xFF)) {
            _hum = data[0];
            _temp = data[2];
            _ok = true;
        } else {
            _ok = false;
        }
        _lastRead = now;
    }

    float temp() { return _temp; }
    float hum() { return _hum; }
    bool ok() override { return _ok; }

    String read() override {
        if (!_ok) return "ERROR";
        return "T=" + String(_temp, 1) + ",H=" + String(_hum, 1);
    }

    String status() override {
        return _ok ? "ALIVE" : "ERROR:CHECKSUM_OR_TIMEOUT";
    }
};

class BatteryMonitor : public Sensor {
private:
    float _voltage = 0.0;
    const float _res1 = 100000.0; // 100k
    const float _res2 = 10000.0;  // 10k
    const float _vref = 5.0;

public:
    void begin() override {
        pinMode(BATT_PIN, INPUT);
    }

    void update() override {
        int raw = analogRead(BATT_PIN);
        float vout = (raw * _vref) / 1024.0;
        _voltage = vout / (_res2 / (_res1 + _res2));
    }

    float voltage() { return _voltage; }

    String read() override {
        return String(_voltage, 2);
    }

    String status() override {
        return (_voltage > 0) ? "ALIVE" : "ERROR:NO_VOLTAGE";
    }

    bool ok() override { return (_voltage > 0); }
};

// --- Global Objects ---
ShtSensor sht;
Dht11Sensor dht1(DHT1_PIN);
Dht11Sensor dht2(DHT2_PIN);
Dht11Sensor dht3(DHT3_PIN);
Dht11Sensor dht4(DHT4_PIN);
BatteryMonitor batt;

uint8_t resetReason = 0;
String inputBuffer = "";

void printResetReason() {
    if (resetReason & (1 << PORF))  Serial.print("POR+");
    if (resetReason & (1 << EXTRF)) Serial.print("EXT+");
    if (resetReason & (1 << BORF))  Serial.print("BOR+");
    if (resetReason & (1 << WDRF))  Serial.print("WDT+");
    if (resetReason == 0)           Serial.print("UNKNOWN+");
}

void setup() {
    resetReason = MCUSR;
    MCUSR = 0;
    wdt_disable();

    Serial.begin(BAUD_RATE);

    pinMode(RELAY_PIN, OUTPUT);
    digitalWrite(RELAY_PIN, LOW);
    // Cross-circuit hard reboot relay (Pin 38): de-energized at boot so the
    // OTHER circuit (Main) has power. Drive LOW idle, pulse HIGH for 2s to
    // engage the cut. (Inverted polarity 2026-05-30 — paired with 2k pull-down
    // on the relay-board IN so floating-Mega state is also cascade-safe LOW.)
    pinMode(HARD_REBOOT_PIN, OUTPUT);
    digitalWrite(HARD_REBOOT_PIN, LOW);

    sht.begin();
    dht1.begin();
    dht2.begin();
    dht3.begin();
    dht4.begin();
    batt.begin();

    // Enable Watchdog (SPEC-005)
    wdt_enable(WDTO_4S);

    Serial.print("READY:HEALTH_MEGA:v2.2:RST=");
    printResetReason();
    Serial.println("");
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
    else if (cmd == "STATUS") {
        sht.update();
        dht1.update();
        dht2.update();
        dht3.update();
        dht4.update();
        batt.update();
        Serial.print("STATUS:OK:RELAY=");
        Serial.print(digitalRead(RELAY_PIN) == HIGH ? "ON" : "OFF");
        Serial.print(",SHT_T=");
        Serial.print(sht.temp(), 1);
        Serial.print(",SHT_H=");
        Serial.print(sht.hum(), 1);
        Serial.print(",DHT1_T=");
        Serial.print(dht1.temp(), 1);
        Serial.print(",DHT1_H=");
        Serial.print(dht1.hum(), 1);
        Serial.print(",DHT2_T=");
        Serial.print(dht2.temp(), 1);
        Serial.print(",DHT2_H=");
        Serial.print(dht2.hum(), 1);
        Serial.print(",DHT3_T=");
        Serial.print(dht3.temp(), 1);
        Serial.print(",DHT3_H=");
        Serial.print(dht3.hum(), 1);
        Serial.print(",DHT4_T=");
        Serial.print(dht4.temp(), 1);
        Serial.print(",DHT4_H=");
        Serial.print(dht4.hum(), 1);
        Serial.print(",BATT=");
        Serial.print(batt.read());
        Serial.println(",WD=ON");
    }
    else if (cmd == "SHT:READ") {
        sht.update();
        Serial.print("SHT:OK:");
        Serial.println(sht.read());
    }
    else if (cmd == "DHT1:READ") {
        dht1.update();
        Serial.print("DHT1:OK:");
        Serial.println(dht1.read());
    }
    else if (cmd == "DHT2:READ") {
        dht2.update();
        Serial.print("DHT2:OK:");
        Serial.println(dht2.read());
    }
    else if (cmd == "DHT3:READ") {
        dht3.update();
        Serial.print("DHT3:OK:");
        Serial.println(dht3.read());
    }
    else if (cmd == "BATT:READ") {
        batt.update();
        Serial.print("BATT:OK:");
        Serial.print(batt.read());
        Serial.println(" V");
    }
    else if (cmd == "REBOOT:SYS") {
        // Pulses the cross-circuit reboot relay on D38.
        // Inverted polarity 2026-05-30: idle LOW (relay de-energized, Main has
        // power), drive HIGH for 2s to energize the relay (cut Main power),
        // then return LOW to release. WDT-safe via 50ms delay slices.
        Serial.println("REBOOT:OK:PULSING");
        digitalWrite(HARD_REBOOT_PIN, HIGH);
        unsigned long t0 = millis();
        while (millis() - t0 < 2000) { wdt_reset(); delay(50); }
        digitalWrite(HARD_REBOOT_PIN, LOW);
        Serial.println("REBOOT:OK:DONE");
    }
    else if (cmd == "RESETINFO") {
        Serial.print("RESETINFO:OK:RST=");
        printResetReason();
        Serial.println("");
    }
    else {
        Serial.print("ERROR:UNKNOWN_CMD:");
        Serial.println(cmd);
    }
}

void loop() {
    wdt_reset();

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
