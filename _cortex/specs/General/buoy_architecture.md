# OceanPulse Buoy Architecture: Dual-Redundant System
**Version:** 1.0 (Draft)
**Design Philosophy:** High Availability / "Watchdog" Redundancy.

## High-Level Overview
The buoy operates on two completely isolated electrical and logic circuits. Each circuit processes specific data and communicates via its own LoRa link. Critical stability is achieved via a **Cross-Relay Topology**, allowing each system to hard-reset the other remotely.

---

## 1. System A: The "Mission" Circuit (Main Processing)
**Role:** Heavy compute, Image Analysis, Scientific Data.
**Hardware:**
*   **SBC:** Raspberry Pi 5 (4GB)
*   **MCU:** Arduino (e.g., Nano/Uno) - *Acts as Sensor Hub & ADC.*
*   **Comms:** LoRa Transceiver A (Primary Data Link).

### Responsibilities
1.  **Vision Stack:**
    *   Control UV 365nm LED Array.
    *   Capture images via Pi Camera 3.
    *   Run OpenCV algorithms (Day/Night detection).
2.  **External Sensors (Underwater):**
    *   *Dissolved Oxygen, Salinity, Temperature, Depth.*
    *   *Current Direction (Flow).*
    *   *Note: Arduino aggregates these (via I2C/UART/RS485) and sends clean data to Pi 5.*
3.  **Primary Telemetry:**
    *   Packages Sensor Data + Oil Alerts.
    *   Sends to Onshore Gateway via LoRa A.

---

## 2. System B: The "Health" Circuit (Internal Monitoring)
**Role:** System Supervision, Environment Safety, Power Management.
**Hardware:**
*   **SBC:** Raspberry Pi 3 B+ (Lower Power).
*   **MCU:** Arduino (e.g., Nano/Uno) - *Acts as Hardware Watchdog & ADC.*
*   **Comms:** LoRa Transceiver B (Command & Control Link).

### Responsibilities
1.  **Internal Environment:**
    *   *Internal Humidity & Temperature* (Detect leaks/condensation).
    *   *Water Ingress Switch* (Bilge alarm).
2.  **Power Telemetry:**
    *   *Battery Voltage (Main Bank).*
    *   *Solar Input Voltage/Amperage.*
    *   *System A Current Draw.*
3.  **Crash Stability:**
    *   Listens for "Heartbeats" from System A locally (GPIO/Serial).
    *   Listens for "Restart A" commands via LoRa B.

---

## 3. Power Architecture: Single Source, Dual Distribution
**Concept:** A robust, central power bank feeds both systems via a Common Power Bus.
*   **Source:** Single high-capacity Solar Panel Array + MPPT Controller.
*   **Storage:** Single LiFePO4 Battery Bank (sized for Sagres winter autonomy).
*   **Emergency Backup:** **System B UPS**. A dedicated UPS HAT with an 18650 cell allows System B to send a "Last Gasp" distress signal if the main battery/bus fails.
*   **Distribution:** 
    *   **Common Bus:** 12V DC (Main).
    *   **Branch A:** Fused connection -> **Relay B (NC)** -> Voltage Regulator (5V) -> **System A**.
    *   **Branch B:** Fused connection -> **Relay A (NC)** -> Voltage Regulator (5V) -> **System B**.

## 4. The Cross-Watchdog Logic (Relay Control)

To prevent a "Zombie Buoy" (where the CPU freezes but consumes power), each system controls the power rail of the other via a **Normally Closed (NC) Relay**.

### Wiring Logic
*   **Relay A (Controlled by Sys A):** Cuts power to -> **System B Branch**.
*   **Relay B (Controlled by Sys B):** Cuts power to -> **System A Branch**.

### Operational Scenarios
1.  **Scenario: Main System Freeze (Vision Code Infinite Loop)**
    *   Operator notices System A stopped sending data.
    *   Operator sends command via LoRa B: `CMD_RESTART_A`.
    *   System B receives command -> Energizes Relay B for 5 seconds (Cutting power to A) -> De-energizes Relay B (Restoring power).
    *   System A reboots fresh.

2.  **Scenario: Total Blackout Prevention**
    *   Relays are **Normally Closed**. If System B crashes and loses power, the relay snaps CLOSED, ensuring System A *remains powered* (and vice-versa). We default to "ON".

---

## 5. Mechanical & Hull Layout (Revised Jan 2026)

### The "Split" Internal Configuration
Due to the size of the 50Ah LiFePO4 battery, it does **not** fit inside the primary IP68 Electronics Box.
*   **Electronics Box:** Relocated from Center -> **Side Offset**. Contains Pis, Arduinos, Relays.
*   **Battery Bank:** Mounted on the **Opposite Side** of the frame to act as counter-ballast.
*   **Environmental Exposure:** The battery is shielded from direct splash/sun but sits in **100% Humidity/Salt Air**.
    *   **Mitigation:** Battery terminals must be potted with **Liquid Electrical Tape**.
    *   **Frame Mod:** New mounting holes required. Must be treated with **Cold Galvanizing Zinc** to prevent rust.

## 6. Communication Infrastructure (3-Tier Link)

### Tier 1: Offshore (The Buoy)
**Hardware:** Pi 5 + Pi 3 + LoRa Modules.
**Role:** Data collection, image analysis, and LoRa transmission.

### Tier 2: Onshore Relay (The "Bridge")
**Hardware:** **Raspberry Pi Zero 2 W** + LoRa Module.
**Location:** Coastal site with line-of-sight to the buoy.
**Role:** Receives LoRa packets from the buoy and re-broadcasts them over **WiFi** to the Lab Hub.

### Tier 3: Lab Hub (The "Brain")
**Hardware:** **Raspberry Pi 4 Model B (1GB)** + 4G/LTE Modem.
**Location:** The main shipping container lab.
**Role:** Central command center. Aggregates data, serves the web dashboard, and provides the internet uplink for remote monitoring.
