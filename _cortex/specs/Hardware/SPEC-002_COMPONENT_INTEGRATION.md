# SPEC-002: Component Integration & Serial Protocol

**Status:** APPROVED
**Priority:** HIGH
**Owner:** Systems_Architect + Embedded_Engineer
**Created:** 2026-01-31
**References:** SPEC-000 (Target Architecture)

---

## 1. Purpose

Define the hardware connections, serial protocol, and test firmware for OceanPulse Phase 1 prototype validation.

---

## 2. Current Hardware Setup (As Connected)

### 2.1 Main Circuit

```
┌───────────────────────────────────────────────────────────────────┐
│                         MAIN CIRCUIT                              │
│                                                                   │
│                      ┌─────────────────┐                          │
│       USB ┌─────────►│ Raspberry Pi    │◄─────────┐ USB           │
│           │          │ (main)          │          │               │
│           │          │                 │          │               │
│           │          │ WiFi: Connected │          │               │
│           │          └────────┬────────┘          │               │
│           │                   │ LAN               │               │
│  ┌────────┴───────┐           │          ┌───────┴────────┐       │
│  │ LoRa Board     │           │          │ Arduino Mega   │       │
│  │                │           │          │                │       │
│  └────────────────┘           │          │ Pin 2: Relay   │       │
│                               │          │ A0: TDS (3.3V) │       │
│                               │          └────────────────┘       │
└───────────────────────────────┼───────────────────────────────────┘
                                │
                                │
┌───────────────────────────────┼───────────────────────────────────┐
│                               │                                   │
│                      ┌────────┴────────┐                          │
│       USB ┌─────────►│ Raspberry Pi    │◄─────────┐ USB           │
│           │          │ (health)        │          │               │
│           │          │                 │          │               │
│           │          │ WiFi: Connected │          │               │
│           │          └─────────────────┘          │               │
│           │                                       │               │
│  ┌────────┴───────┐                      ┌───────┴────────┐       │
│  │ LoRa Board     │                      │ Arduino Mega   │       │
│  │                │                      │ (identical)    │       │
│  └────────────────┘                      └────────────────┘       │
│                                                                   │
│                         HEALTH CIRCUIT                            │
└───────────────────────────────────────────────────────────────────┘
```

### 2.2 Connection Summary

| Circuit | Component | Connects To | Interface | Port/Pin |
|---------|-----------|-------------|-----------|----------|
| **Main** | LoRa Board | Pi (main) | USB | /dev/ttyUSB0 (verify) |
| **Main** | Arduino Mega | Pi (main) | USB | /dev/ttyACM0 (verify) |
| **Main** | Test Relay | Arduino Mega | Digital | Pin 2 |
| **Main** | Test TDS Sensor | Arduino Mega | Analog | A0 (3.3V power) |
| **Health** | LoRa Board | Pi (health) | USB | /dev/ttyUSB0 (verify) |
| **Health** | Arduino Mega | Pi (health) | USB | /dev/ttyACM0 (verify) |
| **Inter-Pi** | LAN Cable | Both Pis | Ethernet | Direct connection |
| **Network** | WiFi | Both Pis | Wireless | Home network |

> **Key:** Pi is the hub. Both LoRa and Arduino connect directly to Pi via USB (parallel, not serial).

---

## 3. Serial Protocol (Pi ↔ Arduino)

### 3.1 Physical Layer

| Parameter | Value |
|-----------|-------|
| Baud Rate | 115200 |
| Data Bits | 8 |
| Parity | None |
| Stop Bits | 1 |
| Flow Control | None |

### 3.2 Message Format

```
<CMD>:<PARAM>\n

Examples:
  RELAY:ON\n      → Turn relay ON
  RELAY:OFF\n     → Turn relay OFF
  TDS:READ\n      → Request TDS reading
  PING\n          → Heartbeat check
```

### 3.3 Response Format

```
<CMD>:<STATUS>:<VALUE>\n

Examples:
  RELAY:OK:ON\n       → Relay turned on successfully
  RELAY:OK:OFF\n      → Relay turned off successfully
  TDS:OK:523\n        → TDS reading is 523
  PING:OK:ALIVE\n     → Arduino responsive
  ERROR:<msg>\n       → Error occurred
```

---

## 4. Test Firmware Requirements

### 4.1 Arduino Mega (Main Circuit)

**File:** `firmware/main_mega/main_mega.ino`

| Feature | Description | Priority |
|---------|-------------|----------|
| Serial Init | 115200 baud, listen for commands | Must |
| Relay Control | Pin 2, respond to RELAY:ON/OFF | Must |
| TDS Read | A0, respond to TDS:READ with raw value | Must |
| Heartbeat | Respond to PING with PING:OK:ALIVE | Must |
| Error Handling | Return ERROR:<msg> on invalid command | Should |

### 4.2 Arduino Mega (Health Circuit)

**File:** `firmware/health_mega/health_mega.ino`

| Feature | Description | Priority |
|---------|-------------|----------|
| Serial Init | 115200 baud, listen for commands | Must |
| Heartbeat | Respond to PING with PING:OK:ALIVE | Must |
| Restart Relay | [Future] Control main circuit power | Phase 1+ |

### 4.3 Raspberry Pi (Main)

**File:** `bridge/main_bridge.py`

| Feature | Description | Priority |
|---------|-------------|----------|
| Serial Connect | Open /dev/ttyACM0 at 115200 | Must |
| Send Commands | RELAY:ON, RELAY:OFF, TDS:READ | Must |
| Parse Responses | Extract status and values | Must |
| LoRa TX | [Future] Forward to onshore | Phase 1+ |

### 4.4 Raspberry Pi (Health)

**File:** `bridge/health_bridge.py`

| Feature | Description | Priority |
|---------|-------------|----------|
| Serial Connect | Open /dev/ttyACM0 at 115200 | Must |
| Heartbeat | Periodic PING to Arduino | Must |
| LAN Comms | [Future] Communicate with Main Pi | Phase 1+ |

---

## 5. Test Sequence

### 5.1 Basic Validation

```
1. Upload main_mega.ino to Main Arduino
2. Upload health_mega.ino to Health Arduino
3. Run main_bridge.py on Main Pi
4. Execute test sequence:

   a) PING → Expect PING:OK:ALIVE
   b) TDS:READ → Expect TDS:OK:<value>
   c) RELAY:ON → Expect RELAY:OK:ON (verify LED/click)
   d) RELAY:OFF → Expect RELAY:OK:OFF

5. Repeat for Health circuit (PING only for now)
```

### 5.2 Success Criteria

- [ ] Main Arduino responds to PING
- [ ] Main Arduino returns TDS readings
- [ ] Main Arduino controls relay (ON/OFF verified)
- [ ] Health Arduino responds to PING
- [ ] Both Pis can communicate with their Arduinos
- [ ] Pis can reach each other via LAN (ping test)

---

## 6. File Structure

```
oceanpulse_phase_one/
├── firmware/
│   ├── main_mega/
│   │   └── main_mega.ino
│   └── health_mega/
│       └── health_mega.ino
├── bridge/
│   ├── main_bridge.py
│   └── health_bridge.py
└── _cortex/
    └── specs/
        └── Hardware/
            └── SPEC-002_COMPONENT_INTEGRATION.md
```

---

## 7. Role Assignments

| Task | Role | Agent |
|------|------|-------|
| Spec maintenance | Systems_Architect | CLAUDE/GEMINI |
| Arduino firmware | Embedded_Engineer | CLAUDE/GEMINI |
| Pi bridge scripts | Network_Engineer | CLAUDE/GEMINI |
| Deploy tooling | Embedded_Engineer | CLAUDE/GEMINI |

---

## 8. Automated Development Pipeline

Embedded_Engineer must be able to **write, deploy, flash, and test** firmware automatically without manual intervention.

### 8.1 Target Systems (from MEMORY_BANK.md)

| System | Hostname | IP | User | Pass | Arduino Port |
|--------|----------|-----|------|------|--------------|
| **Main Pi** | main | 192.168.43.37 | lab | 777 | /dev/ttyACM0 |
| **Health Pi** | health | 192.168.43.50 | router | 777 | /dev/ttyACM0 |

### 8.2 Required Tools on Each Pi

```bash
# Install on both Pis:
sudo apt update
sudo apt install -y arduino-cli python3-serial

# Configure arduino-cli
arduino-cli config init
arduino-cli core update-index
arduino-cli core install arduino:avr

# Add user to dialout for serial access
sudo usermod -a -G dialout $USER
```

### 8.3 SSH Configuration (Dev Machine)

```bash
# ~/.ssh/config (add these entries)
Host main
    HostName 192.168.43.37
    User lab
    StrictHostKeyChecking no

Host health
    HostName 192.168.43.50
    User router
    StrictHostKeyChecking no

# For passwordless access (recommended):
ssh-copy-id lab@192.168.43.37
ssh-copy-id router@192.168.43.50
```

### 8.4 Deploy & Flash Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                  EMBEDDED ENGINEER WORKFLOW                      │
│                                                                  │
│  1. WRITE      firmware/main_mega/main_mega.ino                 │
│       │                                                          │
│       ▼                                                          │
│  2. DEPLOY     scp firmware/ → Pi:/tmp/firmware/                │
│       │                                                          │
│       ▼                                                          │
│  3. FLASH      ssh Pi "arduino-cli compile && upload"           │
│       │                                                          │
│       ▼                                                          │
│  4. TEST       ssh Pi "python3 test_serial.py"                  │
│       │                                                          │
│       ▼                                                          │
│  5. VERIFY     Check output: PING:OK:ALIVE                      │
└─────────────────────────────────────────────────────────────────┘
```

### 8.5 Deployment Scripts

**File:** `firmware/deploy.sh`

```bash
#!/bin/bash
# Deploy and flash firmware to OceanPulse Pis

set -e

MAIN_PI="lab@192.168.43.37"
HEALTH_PI="router@192.168.43.50"
REMOTE_DIR="/tmp/oceanpulse_firmware"
BOARD="arduino:avr:mega"
PORT="/dev/ttyACM0"

deploy_main() {
    echo "=== Deploying to MAIN Pi ==="
    ssh $MAIN_PI "mkdir -p $REMOTE_DIR"
    scp -r firmware/main_mega $MAIN_PI:$REMOTE_DIR/
    ssh $MAIN_PI "cd $REMOTE_DIR/main_mega && arduino-cli compile -b $BOARD && arduino-cli upload -b $BOARD -p $PORT"
    echo "=== Main firmware flashed ==="
}

deploy_health() {
    echo "=== Deploying to HEALTH Pi ==="
    ssh $HEALTH_PI "mkdir -p $REMOTE_DIR"
    scp -r firmware/health_mega $HEALTH_PI:$REMOTE_DIR/
    ssh $HEALTH_PI "cd $REMOTE_DIR/health_mega && arduino-cli compile -b $BOARD && arduino-cli upload -b $BOARD -p $PORT"
    echo "=== Health firmware flashed ==="
}

test_main() {
    echo "=== Testing MAIN Arduino ==="
    ssh $MAIN_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

test_health() {
    echo "=== Testing HEALTH Arduino ==="
    ssh $HEALTH_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

case "$1" in
    main)   deploy_main ;;
    health) deploy_health ;;
    all)    deploy_main && deploy_health ;;
    test)   test_main && test_health ;;
    *)      echo "Usage: $0 {main|health|all|test}" ;;
esac
```

### 8.6 Quick Test Script

**File:** `firmware/test_serial.py`

```python
#!/usr/bin/env python3
"""Quick serial test for Arduino firmware"""

import serial
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
BAUD = 115200

def test():
    ser = serial.Serial(PORT, BAUD, timeout=2)
    time.sleep(2)  # Wait for Arduino reset

    # Clear buffer
    ser.reset_input_buffer()

    # Test PING
    ser.write(b'PING\n')
    response = ser.readline().decode().strip()
    print(f"PING -> {response}")
    assert response == "PING:OK:ALIVE", f"PING failed: {response}"

    print("All tests passed!")
    ser.close()

if __name__ == "__main__":
    test()
```

### 8.7 Embedded_Engineer Jurisdiction Update

To support this workflow, Embedded_Engineer jurisdiction extends to:

| Path | Purpose |
|------|---------|
| `firmware/` | Arduino sketches |
| `firmware/deploy.sh` | Deployment script |
| `firmware/test_serial.py` | Test utilities |

---

*This spec defines the foundation for all hardware integration in OceanPulse Phase 1.*
