# OceanPulse Firmware Specification: Phase 1 (Meshtastic Integrated)

**Version:** 1.0.0
**Status:** DRAFT
**Architecture:** Distributed Dual-System (System A + System B) over LoRa Mesh.

---

## 1. Core Philosophy: "Mesh-First" Telemetry
The buoy utilizes the **Meshtastic** open-source protocol as its primary communication layer. This provides out-of-the-box encryption (AES-256), mesh routing (future-proofing for Phase 2), and mobile app integration for debugging.

*   **Frequency:** 869.525 MHz (EU 10% Duty Cycle Band).
*   **Modulation:** LoRa "LongFast" or Custom High-Bandwidth preset.
*   **Hardware:** Seeed LoRa-E5 Mini (STM32WLE5) flashed with Meshtastic Firmware.

---

## 2. System A: Mission Controller (Raspberry Pi 5)
**Role:** High-Level Compute, Computer Vision, Science Data Aggregation.

### 2.1. Interfaces
*   **I2C Bus:**
    *   Atlas Scientific EZO-EC (Salinity) - Address: `0x64`
    *   Atlas Scientific EZO-DO (Dissolved Oxygen) - Address: `0x61`
    *   Blue Robotics Bar30 (Depth) - Address: `0x76`
*   **USB/Serial:**
    *   **Meshtastic Radio A:** /dev/ttyUSB0 (Python API Control).
    *   **Arduino Mega A:** /dev/ttyACM0 (Watchdog Heartbeat & Relay Control).
*   **CSI:** DFRobot IMX378 Camera.
*   **GPIO/Safety:**
    *   **Input:** 3x PIR Motion Sensors (Safety Interlock).
    *   **Output:** Amber Warning Beacon (MOSFET Control).
    *   **Output:** UV Array Trigger (via NO Relay).

### 2.2. Logic Flow (Python Service)
1.  **Wake Cycle:** Power up from "Nap" state (controlled by Arduino or Cron).
2.  **Sensor Sampling:** Read Salinity, DO, Depth (Average of 10 samples).
3.  **Vision Pipeline (Safety Enforced):**
    *   **Safety Check:** Read PIRs. If Active -> ABORT.
    *   **Pre-Flash Scan:** Capture High-ISO visible image. Detect Nav Lights.
    *   **Warn:** Flash Amber Beacon (2.0s).
    *   **Capture:** Trigger UV Pulse (<200ms) + Shutter.
    *   **Process:** Run Oil Detection Algorithm (OpenCV/YOLO).
    *   Output: `[Count, TotalArea, BoundingBox1, BoundingBox2...]`.
4.  **Packet Construction:** Format data into concise string/bytes.
    *   `"M:OIL=1000;SAL=35.5;DO=6.8;DEP=4.2"`
5.  **Transmission:** Push packet to Meshtastic via Python API (`interface.sendText()`).
6.  **Sleep:** Handshake with Arduino Watchdog -> Shutdown.

---

## 3. System B: Health Monitor (Raspberry Pi 3)
**Role:** Life Support, Environment Safety, Power Management, Remote Reset.

### 3.1. Interfaces
*   **I2C Bus:**
    *   3x BME280 (Internal Temp/Hum/Pressure).
    *   4x INA219 (Voltage/Current: Solar, Batt, SysA, SysB).
    *   Adafruit BNO055 (IMU/Tilt).
*   **USB/Serial:**
    *   **Meshtastic Radio B:** /dev/ttyUSB0 (Command Channel).
    *   **Victron MPPT:** /dev/ttyUSB1 (VE.Direct Hex Protocol).
    *   **Arduino Mega B:** /dev/ttyACM0 (Watchdog).

### 3.2. Logic Flow (Python Service)
1.  **Continuous Monitoring:** Loop every 60 seconds.
2.  **Health Check:** 
    *   Read Voltages (Is Battery < 11.5V? -> Low Power Mode).
    *   Read Humidity (Is Humidity > 90%? -> LEAK ALERT).
    *   Read IMU (Is Tilt > 45deg? -> CAPSIZE ALERT).
3.  **Heartbeat Check:** Listen for System A heartbeat on GPIO/Serial. If missing for > 15 mins -> Send "Reset A" command to Arduino.
4.  **Telemetry:** Broadcast Health Packet via Meshtastic.
    *   `"H:BAT=13.2;SOL=45W;HUM=45%;TILT=2"`
5.  **Command Listener:** Listen to Meshtastic for "Admin Packets" (e.g., `CMD:RESTART_A`).

---

## 4. Microcontroller (Arduino Mega) Firmware
**Role:** Hardware Watchdog, ADC, Hard Relay Control.
**Codebase:** C++ (PlatformIO).

### 4.1. Responsibilities
1.  **Watchdog Timer:** If Pi does not toggle a specific GPIO pin every 5 minutes -> Hard Cut Power via Relay.
2.  **Power Sequencing:** Manage the orderly startup/shutdown of the Pis to prevent SD card corruption.
3.  **Analog Redundancy:** Read raw analog voltage of 12V bus as a backup to the I2C sensors.

---

## 5. Packet Structure (Meshtastic Text)
To simplify Phase 1, we will use ASCII Key-Value pairs inside encrypted Meshtastic payloads.

| Type | Prefix | Format | Example | Frequency |
| :--- | :--- | :--- | :--- | :--- |
| **Mission** | `M:` | `OIL=x;SAL=x;DO=x` | `M:OIL=0;SAL=35;DO=7` | 5-15 min |
| **Health** | `H:` | `BAT=x;SOL=x;HUM=x` | `H:BAT=12.8;SOL=100;HUM=40` | 1-5 min |
| **Alert** | `A:` | `ERR=code` | `A:ERR=LEAK_DETECTED` | Immediate |
| **Command** | `C:` | `TARGET=x;ACT=x` | `C:TARGET=A;ACT=REBOOT` | On Demand |

---

## 6. Development Roadmap
1.  **Step 1:** Flash Meshtastic onto LoRa-E5 Minis and verify Mesh link (Phone <-> Phone).
2.  **Step 2:** "Hello World" Python script on Pi 5 sending text to Mesh.
3.  **Step 3:** Integrate Atlas Sensors (I2C) into Python script.
4.  **Step 4:** Integrate Victron VE.Direct into System B script.
5.  **Step 5:** Build the "Watchdog" Arduino Sketch.
