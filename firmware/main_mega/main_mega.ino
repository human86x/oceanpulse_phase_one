/*
 * OceanPulse Main Mega Firmware v3.7
 * SPEC-005 + SPEC-011 + SPEC-035 — Atlas EZO-EC + UV Hardware Safety Interlock
 *
 * v3.7 vs v3.6 (SPEC-035 §2.1.1 post-swap polarity correction, 2026-06-07):
 *   - Pin 30 polarity inverted to match deployed relay module after 2026-06-06 swap.
 *     Active-HIGH = brake engaged (UV cut). Active-LOW = brake released (UV pass).
 *     Empirically verified by Human: previous v3.6 wrote LOW for "engaged" but the
 *     swapped relay's contact orientation made LOW → closed → UV-passes, inverting
 *     the safety semantics. v3.7 restores correct safety meaning without any frame
 *     access (engage_pin → HIGH, release_pin → LOW; no other firmware logic change).
 *   - Reset reason line now reports v3.7 so deploy/reflash is visible from PING.
 *
 * Wiring (post-swap, 2026-06-07):
 *   - Mega D30 → safety relay coil drive (Active-HIGH = engaged = UV cut)
 *   - Mega D31 → reserved (SPEC-035 §2, unused in v1)
 *
 * Polarity / fail-safe verification REQUIRED before UV operation (SPEC-035 §2.2):
 *   1. MCU off → UV power line at 0 V (NO-contact wiring confirmed).
 *   2. Pin 30 floating → UV power line at 0 V.
 *   3. Pin 4 ON + Pin 30 active-HIGH → UV power line at 0 V (safety overrides command).
 *   4. PIR HIGH + R_HEAT armed → Pin 30 HIGH within 75 ms.
 *   5. Ultrasonic < DIST_THR + R_DIST armed → Pin 30 HIGH within 75 ms.
 *
 * Serial Protocol: 115200 baud, 8N1
 */

#include <avr/wdt.h>
#include <EEPROM.h>

#define BAUD_RATE 115200
#define EC_BAUD   9600

// --- Pins ---
#define RELAY_PIN          2
#define INV_RELAY_PIN      3
#define UV_RELAY_PIN       4
#define TRIG_PIN           5
#define ECHO_PIN           6
#define PIR_PIN           22
#define SAFETY_RELAY_PIN  30   // SPEC-035 v2: UV hardware safety interlock (Active-HIGH = brake engaged, post-2026-06-06 relay swap)
#define TDS_PIN          A0
#define BATT_PIN         A1

#define EC_RX_MAX 32

// --- SPEC-035 defaults & EEPROM layout ---
#define SAFETY_EE_MAGIC      0xA5
#define SAFETY_EE_VERSION    0x01
#define SAFETY_EE_BASE       0
#define SAFETY_EE_MAGIC_ADDR (SAFETY_EE_BASE + 0)
#define SAFETY_EE_VER_ADDR   (SAFETY_EE_BASE + 1)
#define SAFETY_EE_HEAT_ARM   (SAFETY_EE_BASE + 2)
#define SAFETY_EE_DIST_ARM   (SAFETY_EE_BASE + 3)
#define SAFETY_EE_DIST_THR   (SAFETY_EE_BASE + 4)  // u16
#define SAFETY_EE_DIST_HYST  (SAFETY_EE_BASE + 6)  // u8
#define SAFETY_EE_DIST_CLR   (SAFETY_EE_BASE + 7)  // u16
#define SAFETY_EE_HEAT_CLR   (SAFETY_EE_BASE + 9)  // u16

#define DEFAULT_HEAT_ARMED   1
#define DEFAULT_DIST_ARMED   1
#define DEFAULT_DIST_THR_CM  150
#define DEFAULT_DIST_HYST_CM 30
#define DEFAULT_DIST_CLR_MS  3000
#define DEFAULT_HEAT_CLR_MS  5000

// --- Sensor Abstraction Layer ---

class Sensor {
public:
    virtual void begin() = 0;
    virtual void update() = 0;
    virtual String read() = 0;
    virtual String status() = 0;
};

class TdsSensor : public Sensor {
private:
    float _vref = 3.3, _adcRange = 1024.0, _temperature = 25.0;
    int _rawValue = 0;
    float _tdsValue = 0.0;
public:
    void begin() override { pinMode(TDS_PIN, INPUT); }
    void setTemperature(float t) { if (t >= 0 && t <= 50) _temperature = t; }
    float getTemperature() { return _temperature; }
    void update() override {
        long sum = 0;
        for (int i = 0; i < 10; i++) { sum += analogRead(TDS_PIN); delay(1); }
        _rawValue = sum / 10;
        float v = _rawValue * 5.0 / _adcRange;
        if (v > _vref) v = _vref;
        float comp = 1.0 + 0.02 * (_temperature - 25.0);
        float vc = v / comp;
        _tdsValue = (133.42*vc*vc*vc - 255.86*vc*vc + 857.39*vc) * 0.5;
        if (_tdsValue < 0) _tdsValue = 0;
    }
    String read() override { return String(_tdsValue, 1); }
    int raw() { return _rawValue; }
    String status() override { return (_tdsValue >= 0) ? "ALIVE" : "ERROR"; }
};

class DistanceSensor : public Sensor {
private:
    float _distance = -1.0;
public:
    void begin() override {
        pinMode(TRIG_PIN, OUTPUT); pinMode(ECHO_PIN, INPUT);
        digitalWrite(TRIG_PIN, LOW);
    }
    // 3-sample average (used by diagnostic + STATUS).
    void update() override {
        long total = 0; int valid = 0;
        for (int i = 0; i < 3; i++) {
            digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
            digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
            digitalWrite(TRIG_PIN, LOW);
            long d = pulseIn(ECHO_PIN, HIGH, 30000);
            if (d > 0) { total += d; valid++; }
            delay(10);
        }
        _distance = (valid == 0) ? -1.0 : ((float)total / valid) * 0.0343 / 2.0;
    }
    // Single-shot (SPEC-035 safety hot path — ≤ ~30 ms worst case).
    float quickRead() {
        digitalWrite(TRIG_PIN, LOW); delayMicroseconds(2);
        digitalWrite(TRIG_PIN, HIGH); delayMicroseconds(10);
        digitalWrite(TRIG_PIN, LOW);
        long d = pulseIn(ECHO_PIN, HIGH, 30000);
        if (d <= 0) { _distance = -1.0; return -1.0; }
        _distance = d * 0.0343 / 2.0;
        return _distance;
    }
    float value() const { return _distance; }
    String read() override { return (_distance < 0) ? String("NO_ECHO") : String(_distance, 1); }
    String status() override { return (_distance >= 0) ? "ALIVE" : "ERROR:NO_ECHO"; }
};

class PirSensor : public Sensor {
private:
    int _motion = 0;
public:
    void begin() override { pinMode(PIR_PIN, INPUT); }
    void update() override { _motion = digitalRead(PIR_PIN); }
    int signal() const { return _motion; }
    String read() override { return _motion ? "MOTION" : "CLEAR"; }
    String status() override { return "ALIVE"; }
};

class BatteryMonitor : public Sensor {
private:
    float _voltage = 0.0;
    const float _r1 = 100000.0, _r2 = 10000.0, _vref = 5.0;
public:
    void begin() override { pinMode(BATT_PIN, INPUT); }
    void update() override {
        int raw = analogRead(BATT_PIN);
        float vout = (raw * _vref) / 1024.0;
        _voltage = vout / (_r2 / (_r1 + _r2));
    }
    String read() override { return String(_voltage, 2); }
    String status() override { return (_voltage > 0) ? "ALIVE" : "ERROR:NO_VOLTAGE"; }
};

// --- Atlas EZO-EC UART (unchanged from v3.4) ---
class AtlasEzoEcUart {
private:
    float _ecValue = -1.0;
    char _lastReply[EC_RX_MAX + 1] = {0};
    char _lastStatus[8] = {0};
    bool _online = false;

    void drain() { while (Serial1.available()) Serial1.read(); }

    int readLine(char *buf, int maxlen, uint16_t timeout_ms) {
        unsigned long start = millis();
        int i = 0;
        while ((millis() - start) < timeout_ms) {
            wdt_reset();
            if (Serial1.available()) {
                char c = Serial1.read();
                if (c == '\r') { buf[i] = 0; return i; }
                if (c == '\n' || c == 0) continue;
                if (i < maxlen - 1) buf[i++] = c;
            }
        }
        buf[i] = 0;
        return i;
    }

public:
    void begin() { Serial1.begin(EC_BAUD); }
    bool online() const { return _online; }
    float ec() const { return _ecValue; }
    const char *lastReply() const { return _lastReply; }
    const char *lastStatus() const { return _lastStatus; }

    bool transact(const char *cmd, uint16_t timeout_ms) {
        memset(_lastReply, 0, sizeof(_lastReply));
        memset(_lastStatus, 0, sizeof(_lastStatus));
        drain();
        Serial1.print(cmd);
        Serial1.write('\r');

        bool sawOk = false;
        bool payloadCaptured = false;
        char line[EC_RX_MAX + 1];
        unsigned long deadline = millis() + timeout_ms;

        while (millis() < deadline) {
            int n = readLine(line, sizeof(line), (uint16_t)(deadline - millis()));
            if (n == 0) {
                if (Serial1.available() == 0) break;
                continue;
            }
            if (line[0] == '*') {
                strncpy(_lastStatus, line, sizeof(_lastStatus) - 1);
                if (strcmp(line, "*OK") == 0) sawOk = true;
                break;
            }
            if (!payloadCaptured) {
                strncpy(_lastReply, line, sizeof(_lastReply) - 1);
                payloadCaptured = true;
            }
        }
        _online = (sawOk || payloadCaptured);
        return sawOk;
    }

    bool probe() {
        bool ok = transact("i", 400);
        return ok || _lastReply[0] != 0;
    }

    bool update() {
        if (!transact("R", 1000)) {
            if (_lastReply[0] == 0) { _online = false; return false; }
        }
        _ecValue = atof(_lastReply);
        return true;
    }
};

// --- SPEC-035: Safety Controller ---
//
// Owns Pin 30. Polled by loop() with fresh sensor values. Evaluates two rules:
//   R_DIST: dist < DIST_THR_CM   (hysteresis-clear at dist ≥ THR + HYST for DIST_CLR_MS)
//   R_HEAT: PIR == HIGH          (clears after HEAT_CLR_MS of continuous LOW)
// Drives SAFETY_RELAY_PIN LOW (brake engaged) when ANY armed rule trips or during boot lockout.
class SafetyController {
private:
    // Config (persisted)
    bool     _heat_armed;
    bool     _dist_armed;
    uint16_t _dist_thr_cm;
    uint8_t  _dist_hyst_cm;
    uint16_t _dist_clr_ms;
    uint16_t _heat_clr_ms;

    // State
    bool _dist_tripped;
    bool _heat_tripped;
    bool _boot_lockout;
    unsigned long _dist_clear_since_ms;
    unsigned long _heat_clear_since_ms;

    // SPEC-035 v2 (2026-06-07): polarity inverted to match deployed relay after swap.
    void engage_pin() { digitalWrite(SAFETY_RELAY_PIN, HIGH); }  // brake on  (UV cut)
    void release_pin() { digitalWrite(SAFETY_RELAY_PIN, LOW); }  // brake off (UV pass)

    void writeU16(int addr, uint16_t v) {
        EEPROM.update(addr,     v        & 0xFF);
        EEPROM.update(addr + 1, (v >> 8) & 0xFF);
    }
    uint16_t readU16(int addr) {
        return (uint16_t)EEPROM.read(addr) | ((uint16_t)EEPROM.read(addr + 1) << 8);
    }

    void loadOrInitConfig() {
        uint8_t magic = EEPROM.read(SAFETY_EE_MAGIC_ADDR);
        uint8_t ver   = EEPROM.read(SAFETY_EE_VER_ADDR);
        if (magic != SAFETY_EE_MAGIC || ver != SAFETY_EE_VERSION) {
            _heat_armed   = DEFAULT_HEAT_ARMED;
            _dist_armed   = DEFAULT_DIST_ARMED;
            _dist_thr_cm  = DEFAULT_DIST_THR_CM;
            _dist_hyst_cm = DEFAULT_DIST_HYST_CM;
            _dist_clr_ms  = DEFAULT_DIST_CLR_MS;
            _heat_clr_ms  = DEFAULT_HEAT_CLR_MS;
            EEPROM.update(SAFETY_EE_MAGIC_ADDR, SAFETY_EE_MAGIC);
            EEPROM.update(SAFETY_EE_VER_ADDR,   SAFETY_EE_VERSION);
            EEPROM.update(SAFETY_EE_HEAT_ARM,   _heat_armed);
            EEPROM.update(SAFETY_EE_DIST_ARM,   _dist_armed);
            writeU16(SAFETY_EE_DIST_THR,   _dist_thr_cm);
            EEPROM.update(SAFETY_EE_DIST_HYST,  _dist_hyst_cm);
            writeU16(SAFETY_EE_DIST_CLR,   _dist_clr_ms);
            writeU16(SAFETY_EE_HEAT_CLR,   _heat_clr_ms);
        } else {
            _heat_armed   = EEPROM.read(SAFETY_EE_HEAT_ARM) ? true : false;
            _dist_armed   = EEPROM.read(SAFETY_EE_DIST_ARM) ? true : false;
            _dist_thr_cm  = readU16(SAFETY_EE_DIST_THR);
            _dist_hyst_cm = EEPROM.read(SAFETY_EE_DIST_HYST);
            _dist_clr_ms  = readU16(SAFETY_EE_DIST_CLR);
            _heat_clr_ms  = readU16(SAFETY_EE_HEAT_CLR);
        }
    }

public:
    void begin() {
        pinMode(SAFETY_RELAY_PIN, OUTPUT);
        engage_pin();                  // boot to safe state FIRST, before anything else
        _boot_lockout = true;
        _dist_tripped = false;
        _heat_tripped = false;
        _dist_clear_since_ms = 0;
        _heat_clear_since_ms = 0;
        loadOrInitConfig();
    }

    // Caller passes fresh sensor values (dist_cm < 0 means NO_ECHO; pir_signal is HIGH/LOW).
    void update(float dist_cm, int pir_signal) {
        unsigned long now = millis();

        // ---- R_DIST ----
        if (_dist_armed) {
            if (dist_cm > 0 && dist_cm < _dist_thr_cm) {
                _dist_tripped = true;
                _dist_clear_since_ms = 0;
            } else if (dist_cm > 0 && dist_cm >= (_dist_thr_cm + _dist_hyst_cm)) {
                if (_dist_clear_since_ms == 0) _dist_clear_since_ms = now;
                if (now - _dist_clear_since_ms >= _dist_clr_ms) {
                    _dist_tripped = false;
                }
            } else {
                // NO_ECHO or in hysteresis dead-band: hold prior tripped state, reset clear timer.
                _dist_clear_since_ms = 0;
            }
        } else {
            _dist_tripped = false;
        }

        // ---- R_HEAT ----
        if (_heat_armed) {
            if (pir_signal == HIGH) {
                _heat_tripped = true;
                _heat_clear_since_ms = 0;
            } else {
                if (_heat_clear_since_ms == 0) _heat_clear_since_ms = now;
                if (now - _heat_clear_since_ms >= _heat_clr_ms) {
                    _heat_tripped = false;
                }
            }
        } else {
            _heat_tripped = false;
        }

        // ---- Boot lockout release ----
        if (_boot_lockout) {
            bool dist_ok = !_dist_armed || (!_dist_tripped && dist_cm > 0);
            bool heat_ok = !_heat_armed || !_heat_tripped;
            if (dist_ok && heat_ok) _boot_lockout = false;
        }

        // ---- Drive relay ----
        if (brakeEngaged()) engage_pin();
        else                release_pin();
    }

    bool brakeEngaged() const {
        return _boot_lockout
            || (_dist_armed && _dist_tripped)
            || (_heat_armed && _heat_tripped);
    }
    bool bootLocked() const { return _boot_lockout; }
    bool distTripped() const { return _dist_tripped; }
    bool heatTripped() const { return _heat_tripped; }

    bool heatArmed() const { return _heat_armed; }
    bool distArmed() const { return _dist_armed; }
    uint16_t distThr() const { return _dist_thr_cm; }
    uint8_t  distHyst() const { return _dist_hyst_cm; }
    uint16_t distClr() const { return _dist_clr_ms; }
    uint16_t heatClr() const { return _heat_clr_ms; }

    void setHeatArmed(bool v) {
        _heat_armed = v;
        EEPROM.update(SAFETY_EE_HEAT_ARM, v ? 1 : 0);
    }
    void setDistArmed(bool v) {
        _dist_armed = v;
        EEPROM.update(SAFETY_EE_DIST_ARM, v ? 1 : 0);
    }
    bool setDistThr(uint16_t v) {
        if (v < 30 || v > 500) return false;
        _dist_thr_cm = v; writeU16(SAFETY_EE_DIST_THR, v); return true;
    }
    bool setDistHyst(uint8_t v) {
        if (v < 5 || v > 100) return false;
        _dist_hyst_cm = v; EEPROM.update(SAFETY_EE_DIST_HYST, v); return true;
    }
    bool setDistClr(uint16_t v) {
        if (v < 500 || v > 10000) return false;
        _dist_clr_ms = v; writeU16(SAFETY_EE_DIST_CLR, v); return true;
    }
    bool setHeatClr(uint16_t v) {
        if (v < 1000 || v > 30000) return false;
        _heat_clr_ms = v; writeU16(SAFETY_EE_HEAT_CLR, v); return true;
    }
};

// --- Globals ---
TdsSensor       tds;
DistanceSensor  dist;
PirSensor       pir;
BatteryMonitor  batt;
AtlasEzoEcUart  ec;
SafetyController safety;

uint8_t resetReason = 0;
String  inputBuffer = "";

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

    // SPEC-035: safety relay FIRST, before any other init. Brake engaged immediately.
    safety.begin();

    Serial.begin(BAUD_RATE);

    pinMode(RELAY_PIN, OUTPUT);     digitalWrite(RELAY_PIN, LOW);
    pinMode(INV_RELAY_PIN, OUTPUT); digitalWrite(INV_RELAY_PIN, LOW);
    pinMode(UV_RELAY_PIN, OUTPUT);  digitalWrite(UV_RELAY_PIN, LOW);

    ec.begin();
    tds.begin();
    dist.begin();
    pir.begin();
    batt.begin();

    wdt_enable(WDTO_4S);

    Serial.print("READY:MAIN_MEGA:v3.7:RST=");
    printResetReason();
    Serial.print(":BRAKE=");
    Serial.println(safety.brakeEngaged() ? "ON" : "OFF");
}

void handleEcCmd(const String &cmd) {
    int lastColon = cmd.lastIndexOf(':');
    String text;
    uint16_t timeout_ms = 1000;
    if (lastColon >= 0) {
        String tail = cmd.substring(lastColon + 1);
        bool tailIsNum = tail.length() > 0;
        for (uint16_t i = 0; i < tail.length(); i++) {
            if (!isDigit(tail[i])) { tailIsNum = false; break; }
        }
        if (tailIsNum) {
            timeout_ms = (uint16_t)constrain(tail.toInt(), 100, 3000);
            text = cmd.substring(0, lastColon);
        } else {
            text = cmd;
        }
    } else {
        text = cmd;
    }
    text.trim();
    if (text.length() == 0 || text.length() > EC_RX_MAX) {
        Serial.println("EC:CMD:ERR:BAD_INPUT");
        return;
    }
    char buf[EC_RX_MAX + 1];
    text.toCharArray(buf, sizeof(buf));

    bool ok = ec.transact(buf, timeout_ms);
    Serial.print("EC:CMD:");
    Serial.print(ok ? "OK" : "ERR");
    Serial.print(":");
    Serial.print(ec.lastStatus()[0] ? ec.lastStatus() : "(no status)");
    Serial.print(":");
    Serial.println(ec.lastReply());
}

void printSafetySnapshot() {
    Serial.print("SAFETY:OK:HEAT=");   Serial.print(safety.heatArmed() ? "ON" : "OFF");
    Serial.print(",DIST=");            Serial.print(safety.distArmed() ? "ON" : "OFF");
    Serial.print(",DIST_THR=");        Serial.print(safety.distThr());
    Serial.print(",DIST_HYST=");       Serial.print(safety.distHyst());
    Serial.print(",DIST_CLR=");        Serial.print(safety.distClr());
    Serial.print(",HEAT_CLR=");        Serial.print(safety.heatClr());
    Serial.print(",BRAKE=");           Serial.print(safety.brakeEngaged() ? "ON" : "OFF");
    Serial.print(",BOOT_LOCK=");       Serial.print(safety.bootLocked() ? "ON" : "OFF");
    Serial.print(",DIST_TRIP=");       Serial.print(safety.distTripped() ? "ON" : "OFF");
    Serial.print(",HEAT_TRIP=");       Serial.println(safety.heatTripped() ? "ON" : "OFF");
}

void handleSafetyCmd(const String &cmd) {
    // cmd is the substring after "SAFETY:"
    if (cmd == "GET") {
        printSafetySnapshot();
        return;
    }
    if (cmd == "READ") {
        // Legacy diagnostic — raw DIST + PIR snapshot.
        dist.update(); pir.update();
        Serial.print("SAFETY:OK:READ:DIST="); Serial.print(dist.read());
        Serial.print(",PIR="); Serial.println(pir.read());
        return;
    }
    if (cmd == "HEAT:ON")  { safety.setHeatArmed(true);  Serial.println("SAFETY:OK:HEAT=ON");  return; }
    if (cmd == "HEAT:OFF") { safety.setHeatArmed(false); Serial.println("SAFETY:OK:HEAT=OFF"); return; }
    if (cmd == "DIST:ON")  { safety.setDistArmed(true);  Serial.println("SAFETY:OK:DIST=ON");  return; }
    if (cmd == "DIST:OFF") { safety.setDistArmed(false); Serial.println("SAFETY:OK:DIST=OFF"); return; }

    if (cmd.startsWith("DIST_THR:")) {
        long v = cmd.substring(9).toInt();
        if (v <= 0 || v > 65535 || !safety.setDistThr((uint16_t)v)) {
            Serial.println("SAFETY:ERR:RANGE:DIST_THR_30_500"); return;
        }
        Serial.print("SAFETY:OK:DIST_THR="); Serial.println(safety.distThr()); return;
    }
    if (cmd.startsWith("DIST_HYST:")) {
        long v = cmd.substring(10).toInt();
        if (v <= 0 || v > 255 || !safety.setDistHyst((uint8_t)v)) {
            Serial.println("SAFETY:ERR:RANGE:DIST_HYST_5_100"); return;
        }
        Serial.print("SAFETY:OK:DIST_HYST="); Serial.println(safety.distHyst()); return;
    }
    if (cmd.startsWith("DIST_CLR:")) {
        long v = cmd.substring(9).toInt();
        if (v <= 0 || v > 65535 || !safety.setDistClr((uint16_t)v)) {
            Serial.println("SAFETY:ERR:RANGE:DIST_CLR_500_10000"); return;
        }
        Serial.print("SAFETY:OK:DIST_CLR="); Serial.println(safety.distClr()); return;
    }
    if (cmd.startsWith("HEAT_CLR:")) {
        long v = cmd.substring(9).toInt();
        if (v <= 0 || v > 65535 || !safety.setHeatClr((uint16_t)v)) {
            Serial.println("SAFETY:ERR:RANGE:HEAT_CLR_1000_30000"); return;
        }
        Serial.print("SAFETY:OK:HEAT_CLR="); Serial.println(safety.heatClr()); return;
    }

    Serial.print("SAFETY:ERR:UNKNOWN:"); Serial.println(cmd);
}

void processCommand(String cmd) {
    cmd.trim();
    cmd.toUpperCase();

    if (cmd == "PING") Serial.println("PING:OK:ALIVE");
    else if (cmd == "UPTIME") { Serial.print("UPTIME:OK:"); Serial.println(millis()); }
    else if (cmd == "TDS:READ") {
        tds.update();
        Serial.print("TDS:OK:"); Serial.print(tds.read()); Serial.println(" ppm");
    }
    else if (cmd == "TDS:RAW") {
        tds.update();
        Serial.print("TDS:RAW:"); Serial.print(tds.raw());
        Serial.print(",V:"); Serial.println(tds.raw() * 5.0 / 1024.0, 3);
    }
    else if (cmd.startsWith("TEMP:SET:")) {
        float t = cmd.substring(9).toFloat();
        tds.setTemperature(t);
        Serial.print("TEMP:OK:"); Serial.println(tds.getTemperature(), 1);
    }
    else if (cmd == "TEMP:GET") { Serial.print("TEMP:OK:"); Serial.println(tds.getTemperature(), 1); }
    else if (cmd == "DIST:READ") {
        dist.update();
        Serial.print("DIST:OK:"); Serial.println(dist.read());
    }
    else if (cmd == "PIR:READ") {
        pir.update();
        Serial.print("PIR:OK:"); Serial.println(pir.read());
    }
    else if (cmd == "BATT:READ") {
        batt.update();
        Serial.print("BATT:OK:"); Serial.print(batt.read()); Serial.println(" V");
    }
    // SPEC-035: SAFETY:* family. Bare "SAFETY" preserved as alias for legacy diagnostic.
    else if (cmd == "SAFETY") {
        // Back-compat alias for old read-only diagnostic. Prefer SAFETY:READ going forward.
        dist.update(); pir.update();
        Serial.print("SAFETY:OK:DIST="); Serial.print(dist.read());
        Serial.print(",PIR="); Serial.println(pir.read());
    }
    else if (cmd.startsWith("SAFETY:")) {
        handleSafetyCmd(cmd.substring(7));
    }
    else if (cmd == "EC:READ") {
        if (!ec.update()) {
            Serial.print("EC:ERR:");
            Serial.print(ec.lastStatus()[0] ? ec.lastStatus() : "OFFLINE");
            Serial.print(":");
            Serial.println(ec.lastReply());
            return;
        }
        Serial.print("EC:OK:"); Serial.print(ec.ec(), 2); Serial.println(" uS");
    }
    else if (cmd == "EC:STATUS") {
        bool p = ec.probe();
        Serial.print("EC:STATUS:");
        Serial.print(p ? "ONLINE" : "OFFLINE");
        Serial.print(":REPLY=");
        Serial.println(ec.lastReply());
    }
    else if (cmd.startsWith("EC:CMD:")) handleEcCmd(cmd.substring(7));
    else if (cmd == "REBOOT:SYS") {
        Serial.println("REBOOT:OK:PULSING");
        digitalWrite(RELAY_PIN, LOW); delay(2000); digitalWrite(RELAY_PIN, HIGH);
        Serial.println("REBOOT:OK:DONE");
    }
    else if (cmd == "RESETINFO") { Serial.print("RESETINFO:OK:RST="); printResetReason(); Serial.println(""); }
    else if (cmd == "UV:ON") {
        digitalWrite(UV_RELAY_PIN, LOW); delay(50); digitalWrite(UV_RELAY_PIN, HIGH);
        Serial.println("UV:OK:TRIGGERED");
    }
    else if (cmd == "UV:OFF") {
        digitalWrite(UV_RELAY_PIN, HIGH);
        Serial.println("UV:OK:OFF");
    }
    else if (cmd.startsWith("UV:PULSE:")) {
        int secs = cmd.substring(9).toInt();
        if (secs < 1 || secs > 30) Serial.println("ERROR:UV_PULSE_RANGE_1_30");
        else {
            Serial.print("UV:OK:PULSE:"); Serial.println(secs);
            digitalWrite(UV_RELAY_PIN, LOW);
            unsigned long start = millis();
            while (millis() - start < (unsigned long)secs * 1000) { wdt_reset(); delay(10); }
            digitalWrite(UV_RELAY_PIN, HIGH);
            Serial.println("UV:OK:PULSE_DONE");
        }
    }
    else if (cmd.startsWith("PIN:HIGH:")) {
        int p = cmd.substring(9).toInt();
        if (p > 1 && p < 54) { pinMode(p, OUTPUT); digitalWrite(p, HIGH); Serial.print("PIN:OK:HIGH="); Serial.println(p); }
        else Serial.println("PIN:ERR:RANGE");
    }
    else if (cmd.startsWith("PIN:LOW:")) {
        int p = cmd.substring(8).toInt();
        if (p > 1 && p < 54) { pinMode(p, OUTPUT); digitalWrite(p, LOW); Serial.print("PIN:OK:LOW="); Serial.println(p); }
        else Serial.println("PIN:ERR:RANGE");
    }
    else if (cmd == "STATUS") {
        tds.update(); dist.update(); batt.update();
        bool ec_ok = ec.update();
        Serial.print("STATUS:OK:RELAY=");
        Serial.print(digitalRead(RELAY_PIN) == HIGH ? "ON" : "OFF");
        Serial.print(",TDS="); Serial.print(tds.read());
        Serial.print("ppm,BATT="); Serial.print(batt.read());
        Serial.print("V,DIST="); Serial.print(dist.read());
        Serial.print(",EC=");
        if (ec_ok) Serial.print(ec.ec(), 2);
        else Serial.print(ec.online() ? "ERR" : "OFFLINE");
        Serial.print(",BRAKE="); Serial.print(safety.brakeEngaged() ? "ON" : "OFF");
        Serial.println(",WD=ON");
    }
    else { Serial.print("ERROR:UNKNOWN_CMD:"); Serial.println(cmd); }
}

// SPEC-035 §3.6: background safety polling.
// 20 Hz (50 ms) when UV control relay is engaged (Pin 4 = LOW), 2 Hz (500 ms) otherwise.
// Uses DistanceSensor::quickRead() (single pulseIn, ~30 ms worst case) to stay non-blocking.
void pollSafety() {
    static unsigned long last_poll_ms = 0;
    unsigned long now = millis();
    bool uv_active = (digitalRead(UV_RELAY_PIN) == LOW);
    unsigned long interval = uv_active ? 50UL : 500UL;
    if (now - last_poll_ms < interval) return;
    last_poll_ms = now;

    float dist_cm = dist.quickRead();
    pir.update();
    safety.update(dist_cm, pir.signal());
}

void loop() {
    wdt_reset();

    pollSafety();

    while (Serial.available()) {
        char c = Serial.read();
        if (c == '\n' || c == '\r') {
            if (inputBuffer.length() > 0) { processCommand(inputBuffer); inputBuffer = ""; }
        } else {
            inputBuffer += c;
            if (inputBuffer.length() > 64) {
                inputBuffer = "";
                Serial.println("ERROR:BUFFER_OVERFLOW");
            }
        }
    }
}
