# OceanPulse Buoy: Hardware Bill of Materials (BOM)

**Design Standard:** Dual-Redundant Architecture (System A/B).
**Environment:** Marine / Port (High Biofouling Risk).
**Power:** Single Central Source (Solar + LiFePO4).

---

## 1. Power System (Central)
*Designed for Sagres Winter Autonomy (2.6 - 3 days with 24/7 Ops).*

*   **Solar Panel:** 2x **60W Offgridtec ETFE-AL Semi-flexible Panels** (Total 120W).
    *   *Mounting:* Mounted on opposite sides of the mast or contoured to the hull.
    *   *Wiring:* Connected in **Parallel** to the MPPT.
    *   *Spec:* Marine-grade ETFE coating, salt-mist resistant, aluminum core.
*   **Battery:** 1x **40Ah - 60Ah LiFePO4 (Lithium Iron Phosphate)**.
    *   *Why:* Deep discharge capability (80-90%), lightweight, safe chemistry.
*   **Charge Controller:** 1x **MPPT Controller (15A)**.
    *   *Interface:* RS485 or UART recommended.
*   **Power Distribution:**
    *   2x **DC-DC Buck Converters (12V -> 5V 5A)**.
    *   1x **Marine Fuse Block (4-6 Gang)**.

---

## 2. System A: Mission Circuit (The "Eye")

### Compute & Control
*   **SBC:** Raspberry Pi 5 4GB (Already in Stock).
*   **MCU:** Arduino Mega 2560 R3 (JOY-IT). *Provides 4 hardware serial ports for robust debugging.*
*   **Storage:** 64GB+ A2 MicroSD.

### Vision Stack
- **Camera:** Arducam B0520 (Sony IMX291) USB Camera.
  - *Reason:* Industrial metal housing, Superior Low Light (Starvis) for UV fluorescence, UVC plug-and-play, M12 lens mount for filters.
  - *Connection:* Direct USB to Raspberry Pi 5.
*   **Housing:** IP68 Waterproof Camera Case.
*   **UV Illumination (Night Detection Only):**

...

---

## 3. System B: Health Circuit (The "Heart")

### Compute & Control
*   **SBC:** Raspberry Pi 3 B+ (In Stock).
*   **Emergency Backup:** **UPS HAT + 18650 Li-ion Cell**. *Provides "Last Gasp" telemetry if main bus fails.*
*   **MCU:** Arduino Mega 2560 R3 (JOY-IT).

### Internal Sensors
*   **Environment:** 3x **BME280** (Temp, Humidity, Pressure) - *Detects seal failure in multiple zones.*
*   **Leak Detection:** **Bilge Float Switch** or Water Contact Probe (Bottom of hull).
*   **Power Monitor:** 4x **INA219 or INA226** (I2C) - *Measures Solar In, Battery, and draws for Sys A & B.*

### Comms B
*   **LoRa:** SX1262 / RFM95 Module (868 MHz EU).
*   **Antenna:** Separate 3dBi Fiberglass Antenna (Frequency diversity if possible, or spatial separation).

---

---

## 4. Stability Hardware (The "Watchdogs")
*   **Relay A:** 5V Relay Module (Normally Closed, 10A). *Controlled by Sys A, Cuts Sys B.*
*   **Relay B:** 5V Relay Module (Normally Closed, 10A). *Controlled by Sys B, Cuts Sys A.*

---

## 5. Enclosure & Connectors
*   **Cable Glands:** IP68 Nylon or Nickel-Plated Brass (Sizes: PG7, PG9, PG11).
*   **Connectors:** **SP13 / SP21 Waterproof Aviation Connectors** (2-pin to 6-pin).
*   **Wiring:** Marine Tinned Copper Wire (18AWG for power, 22AWG for signals).
