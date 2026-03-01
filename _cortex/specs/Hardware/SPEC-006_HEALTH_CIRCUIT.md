# SPEC-006: Health Circuit & Self-Healing (M2)

**Status:** IN PROGRESS
**Priority:** HIGH
**Owner:** Embedded_Engineer + Network_Engineer
**References:** SPEC-004 (Roadmap)

---

## 1. Overview
This specification defines the implementation of health monitoring and self-healing restart mechanisms for the OceanPulse buoy.

---

## 2. LAN Inter-Pi Protocol (Network_Engineer)

### 2.1 Interface Configuration
Both Pis are connected via a direct Ethernet cable. This link provides a redundant communication path independent of the buoy's internal/external WiFi.

- **Subnet:** 10.0.0.0/30
- **Main Pi (System A):** 10.0.0.1
- **Health Pi (System B):** 10.0.0.2

### 2.2 Heartbeat Mechanism
The Main Pi acts as the heartbeat emitter. The Health Pi acts as the watchdog listener.

- **Protocol:** UDP (Unreliable but low overhead)
- **Port:** 5005
- **Payload:** `{"status": "ALIVE", "ts": "ISO8601", "uptime": seconds}`
- **Interval:** 5 seconds

### 2.3 Failsafe Thresholds
- **Warning State:** No heartbeat received for 15 seconds. (Log event).
- **Critical State:** No heartbeat received for 30 seconds. (Trigger self-healing).

### 2.4 Self-Healing Action
When Critical State is reached:
1. Health Pi logs `critical_failure` to internal logs.
2. Health Pi sends `RELAY:ON` to Health Arduino.
3. Health Arduino activates Pin 2 → Main Pi power-cycle.
4. Wait 60 seconds for Main Pi reboot before resuming heartbeat monitoring.

---

## 3. Health Monitoring (Embedded_Engineer)
[PENDING: Definition of internal sensors - temp, humidity, voltage]
