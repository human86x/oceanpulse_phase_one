# SPEC-004: Implementation Roadmap

**Status:** DRAFT (Pending Human Approval)
**Priority:** CRITICAL
**Owner:** Systems_Architect + Human
**Created:** 2026-02-05
**References:** SPEC-000 (Target Architecture)

---

## 1. Purpose

This spec defines the **sequence of milestones** that bridge the current state (partial bench testing) to the completed SPEC-000 vision (autonomous dual-circuit buoy with oil detection).

This is a **roadmap only** -- it defines WHAT to build in WHAT ORDER. Each milestone will have its own detailed spec (SPEC-005 through SPEC-011) defining HOW to build it.

### 1.1 Spec Tree

```
SPEC-000  Target Architecture (North Star - WHAT)
└── SPEC-004  Implementation Roadmap (this file - IN WHAT ORDER)
     ├── SPEC-005  Dev Sensor Platform (M1)
     ├── SPEC-006  Health Circuit & Self-Healing (M2)
     ├── SPEC-007  LoRa Test & Configuration Tool (M2.5)
     ├── SPEC-008  LoRa Communication Chain (M3)
     ├── SPEC-009  Safe-Pulse Oil Detection System (M4)
     ├── SPEC-010  Power Autonomy (M5)
     ├── SPEC-011  Ocean-Grade Sensor Upgrade (M6)
     └── SPEC-012  Integration & Enclosure (M7)
```

---

## 2. Current State (As Of 2026-02-05)

### 2.1 What Works

| Capability | Status | Evidence |
|-----------|--------|----------|
| TDS sensor reading (Main Arduino, Pin A0) | Validated | task_001, SPEC-002 |
| Relay control (Main Arduino, Pin 2) | Validated | task_003, SPEC-002 |
| Serial protocol Pi ↔ Mega (115200 baud) | Working | task_002, SPEC-002 |
| Main Pi online (192.168.43.37) | Online | MEMORY_BANK |
| Health Pi online (192.168.43.49) | Online | MEMORY_BANK |
| Both Pis on same WiFi (WP6) | Connected | REQ-005 |
| Obs Center dashboard (basic) | Running | task_005, task_006 |
| ADT Panel at oceanpulse.pt | Deployed | SPEC-003 |
| Arduinos recovered from undervoltage | Fixed | ATX PSU intervention |

### 2.2 What Does NOT Work Yet

| Capability | Blocker |
|-----------|---------|
| Real water quality sensors (Atlas EZO, Bar30) | Not yet procured/connected |
| Health Arduino sensors (temp, humidity, voltage) | Not yet defined/connected |
| LoRa end-to-end communication | Hardware present but not proven in real conditions |
| UV oil detection system | Not yet built (NE555, PIR, ultrasonic, camera) |
| Solar power system | Not yet procured |
| Waterproof enclosure | Buoy frame failed QC, pending replacement |

### 2.3 Hardware In Lab

| Item | Qty | Notes |
|------|-----|-------|
| Raspberry Pi 5 4GB | 1 | Main Pi |
| Raspberry Pi 3 B+ 1GB | 1 | Health Pi |
| Arduino Mega 2560 R3 | 2 | Main + Health |
| TDS Sensor (dev) | 1 | Pin A0, 3.3V -- dev sensor, not Atlas |
| 5V Relay Module | 2 | Pin 2 |
| LoRa Boards | 2 | Connected via USB (needs real-world testing) |
| LAN Cable (0.25m) | 1 | Pi-to-Pi direct |
| ATX 300W PSU | 1 | Temporary lab power |

---

## 3. Milestones

### M1: Dev Sensor Platform
> *"We can read the ocean (with cheap sensors first)"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-005 (to be written) |
| **Depends On** | Nothing (can start immediately) |
| **Lead Roles** | Embedded_Engineer, Backend_Engineer |
| **Objective** | Build the full sensor-to-dashboard pipeline using cheap dev sensors. Prove the firmware, serial protocol, bridge, and dashboard work end-to-end. Design it sensor-agnostic so the ocean-grade sensors swap in later with minimal rework. |

**Dev Sensors (cheap, available now):**

| Dev Sensor | Simulates | Interface | Final Sensor (later) |
|-----------|-----------|-----------|---------------------|
| TDS sensor (already in lab) | Conductivity/Salinity | Analog (A0) | Atlas EZO EC Kit (RS485) |
| Dallas DS18B20 | Temperature | OneWire | Atlas EZO EC Kit (built-in temp) |
| Cheap pH sensor module | pH/water quality | Analog | Not in SPEC-000 (dev validation only) |

**Key Design Principle: Sensor Abstraction**
The firmware and serial protocol MUST be designed with a **sensor abstraction layer**. Each sensor type has a standard command/response format regardless of the underlying hardware. When the Atlas sensors arrive later, only the low-level driver changes -- the serial protocol, bridge, and dashboard stay the same.

```
Serial Protocol (stable)          Sensor Drivers (swappable)
┌─────────────────────┐          ┌──────────────────────┐
│ TEMP:READ → value   │◄────────│ DS18B20 (now)        │
│                     │          │ Atlas EZO EC (later)  │
│ COND:READ → value   │◄────────│ TDS analog (now)     │
│                     │          │ Atlas EZO EC (later)  │
│ PH:READ → value     │◄────────│ Cheap pH (now)       │
│                     │          │ (dropped later)       │
│ DEPTH:READ → value  │◄────────│ (none now)           │
│                     │          │ Bar30 I2C (later)     │
│ DO:READ → value     │◄────────│ (none now)           │
│                     │          │ Atlas EZO DO (later)  │
└─────────────────────┘          └──────────────────────┘
```

**Key Work:**
- Firmware: sensor abstraction layer + drivers for TDS, DS18B20, cheap pH
- Serial protocol: standardized commands for each sensor type (TEMP:READ, COND:READ, PH:READ, etc.)
- Bridge: forward all sensor data to Obs Center
- Dashboard: display all available sensor readings with clear labels
- Architecture: document the driver interface so ocean-grade swap is straightforward

**Procurement Required:**
- Dallas DS18B20 temperature sensor (~€2-3)
- Cheap pH sensor module (~€10-15)
- 4.7kΩ resistor for DS18B20 pull-up (~€0.10)
- (TDS sensor already in lab)

**Gate Test:**
Leave system running 24h on bench. All 3 dev sensor types (TDS, temperature, pH) reporting to Obs Center dashboard without data gaps or crashes. Serial protocol uses abstracted commands that won't change when real sensors arrive.

---

### M2: Health Circuit & Self-Healing
> *"The buoy can watch itself"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-006 (to be written) |
| **Depends On** | Nothing (can run in parallel with M1) |
| **Lead Roles** | Embedded_Engineer, Network_Engineer |
| **Objective** | Health Arduino monitoring internal conditions, Health Pi bridge operational, cross-restart relay proven |

**Key Work:**
- Health Arduino firmware: read internal temp, humidity, voltage sensors
- Health serial protocol (extend SPEC-002 format)
- Pi-to-Pi LAN communication protocol
- Cross-restart relay: Health relay power-cycles Main circuit (and vice versa)
- Obs Center: health data display panel

**Procurement Required:**
- Internal temp sensors (model TBD from lab stock)
- Humidity sensors (model TBD from lab stock)
- Voltage divider components for voltage monitoring

**Gate Test:**
Kill Main Pi process. Health circuit detects failure and triggers restart relay. Main recovers and resumes data flow automatically.

---

### M2.5: LoRa Test & Configuration Tool
> *"We understand our radio link"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-007 (to be written) |
| **Depends On** | Nothing (can start anytime) |
| **Lead Roles** | Network_Engineer, Frontend_Engineer |
| **Objective** | Build a tool to test, measure, and tune LoRa parameters before committing to a production configuration |

**Key Work:**
- LoRa parameter control (SF, BW, TX power, frequency, coding rate)
- Live metrics display: RSSI, SNR, packet loss, round-trip time
- Range test mode: send N packets, log results
- Configuration profiles: save/load parameter sets
- Test result logging for comparison across runs

**Procurement Required:**
- None (LoRa boards already in lab)

**Gate Test:**
Conduct range test at 3 distances (10m, 100m, 500m). Tool shows RSSI/SNR/packet loss for at least 2 different SF/BW configurations. Results saved and comparable.

---

### M3: LoRa Communication Chain
> *"We can reach the shore"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-008 (to be written) |
| **Depends On** | **M2.5** (need tuned LoRa parameters) |
| **Lead Roles** | Network_Engineer, Backend_Engineer |
| **Objective** | End-to-end data path: Sensor → Mega → Pi → LoRa → Onshore Gateway → Obs Center |

**Key Work:**
- Onshore gateway setup (Pi Zero 2W + LoRa module)
- LoRa packet format: sensor data, health data, commands
- Bidirectional: data upstream, commands downstream
- Backup path: Health LoRa as redundant channel
- Obs Center: receive data via gateway instead of direct WiFi

**Procurement Required:**
- Raspberry Pi Zero 2W (for onshore gateway)
- LoRa module for gateway (LoRa-E5 Mini or matching)
- USB charger for gateway

**Gate Test:**
Move buoy-side hardware 500m from gateway. Sensor data arrives at Obs Center via LoRa. Kill primary LoRa -- data reroutes through Health (backup) LoRa. Commands sent from Obs Center reach Arduino and execute.

---

### M4: Safe-Pulse Oil Detection System
> *"We can safely detect oil"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-009 (to be written) |
| **Depends On** | **M1** (sensor platform firmware foundation), **M3** (alerts need comms) |
| **Lead Roles** | Embedded_Engineer, Systems_Architect |
| **Objective** | Complete UV fluorescence detection system with Triple-Lock safety interlock, camera sync, and edge AI |

**This is the core mission of OceanPulse.** The detection cycle is one atomic, inseparable system:

```
PIR Check → Ultrasonic Check → Warning Strobe (2s) → UV Pulse (≤500ms) → Camera Capture → AI Analysis → Alert
   │              │                                        │
   │              │                                   NE555 Hard-Stop
   │              │                                   (hardware cutoff)
   │              └─ Object <1.5m? → ABORT
   └─ Human heat detected? → HARD LOCK
```

**Key Work:**
- NE555 + 30A relay hard-stop circuit (500ms max pulse, hardware-enforced)
- PIR sensor (HC-SR501 x2) integration -- thermal check, hard lock UV
- Ultrasonic sensor (JSN-SR04T) integration -- proximity veto, <1.5m abort
- Warning strobe integration -- 2-second pre-fire warning
- Green Cell inverter (12V→230V) for UV strobe
- Camera (IMX378) synchronized shutter to UV pulse
- Edge AI on Main Pi -- fluorescence image analysis
- Night Protocol cycle: autonomous 5-10 minute intervals
- Event-driven alerts: oil detected → thumbnail + alert via LoRa

**Procurement Required:**
- HC-SR501 PIR sensors x2 (~€4)
- JSN-SR04T ultrasonic sensor (~€8)
- NE555 timer IC + components (~€5)
- 30A relay module (~€10)
- Warning strobe lamp (amber/red, waterproof) (~€15)
- Green Cell inverter 12V→230V 150W (~€40)
- UV LEDs 10W 365nm COB x4 (~€60) -- already on procurement list
- DFRobot IMX378 camera (~€39) -- already on procurement list

**Gate Test (ALL must pass):**
1. Walk into UV zone → system refuses to fire (100%, every time)
2. Place object <1.5m from ultrasonic → system aborts pulse
3. Remove all obstacles → strobe fires 2s → UV pulses → camera captures
4. NE555 hard-stop: even with Arduino signal held high, UV cuts at ≤500ms
5. Drop thin oil film in test basin → system detects fluorescence and sends alert to Obs Center

---

### M5: Power Autonomy
> *"We can survive at sea"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-010 (to be written) |
| **Depends On** | **M1** + **M2** (need real power draw measurements from actual hardware) |
| **Lead Roles** | Embedded_Engineer, Systems_Architect |
| **Objective** | Solar + battery system sustaining the full buoy for 2-3 days without sun |

**Key Work:**
- LiFePO4 50Ah + Victron MPPT 75/15 + Solar panel integration
- DC-DC converters: 12V→5V for Pis and Arduino
- Marine fuse block for power distribution
- Real power budget measurement (not estimates -- measure actual draw)
- Charging cycle validation
- Low-power modes (if needed to meet autonomy target)

**Procurement Required:**
- LiFePO4 50Ah battery (~€154) -- on procurement list
- Victron MPPT 75/15 (~€72) -- on procurement list
- Solar panels 60W x2 (~€98) -- on procurement list
- DC-DC converters 12V→5V x2 (~€30) -- on procurement list
- Marine fuse block 6-way (~€15) -- on procurement list

**Gate Test:**
Unplug mains power. Full system (both circuits + periodic UV cycle) runs on battery+solar for 48h. Voltage never drops below safe threshold. System resumes full operation after sunrise charging.

---

### M6: Ocean-Grade Sensor Upgrade
> *"Swap in the real sensors"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-011 (to be written) |
| **Depends On** | **M1** (dev sensor platform proven), **M4** (full system pipeline working) |
| **Lead Roles** | Embedded_Engineer |
| **Objective** | Replace dev sensors with ocean-grade Atlas Scientific and Bar30 sensors. Validate the sensor abstraction layer works as designed -- only drivers change, everything else stays. |

**Ocean-Grade Sensors:**
- Atlas Scientific EZO Conductivity Kit (K 1.0) -- Temp + Salinity via RS485
- Atlas Scientific EZO Dissolved Oxygen Kit -- DO via RS485
- Blue Robotics Bar30 -- Pressure/Depth via I2C

**Key Work:**
- RS485-to-TTL wiring for Atlas EZO boards
- I2C wiring for Bar30
- New firmware drivers (replacing TDS/DS18B20/pH drivers)
- Calibration procedures for Atlas sensors
- Remove cheap pH (not needed with Atlas EC)
- Add DEPTH:READ and DO:READ (new capabilities not available with dev sensors)
- Dashboard: update to show full ocean-grade sensor suite

**Procurement Required:**
- Atlas Conductivity Kit K 1.0 (~€253)
- Atlas Dissolved Oxygen Kit (~€390)
- Blue Robotics Bar30 (~€99)
- RS485-to-TTL modules x3 (~€6)

**Gate Test:**
All 5 sensor types (Temp, Conductivity/Salinity, DO, Pressure/Depth) reporting to Obs Center via the same serial protocol and LoRa chain. Stable 24h run. Readings are within expected ranges for the lab environment.

---

### M7: Integration & Enclosure
> *"It's a buoy"*

| Field | Value |
|-------|-------|
| **Detailed Spec** | SPEC-012 (to be written) |
| **Depends On** | **ALL previous milestones** |
| **Lead Roles** | All roles |
| **Objective** | Everything in a waterproof housing, land integration test, controlled water deployment |

**Key Work:**
- Waterproof enclosure (pending replacement buoy frame)
- Weipu connectors for all cable penetrations
- Cable glands for sensor leads
- Physical mounting of all components
- Full system land test (all milestones running together)
- Controlled water deployment test

**Procurement Required:**
- Buoy frame (replacement, pending)
- Weipu SP21 connectors x3 sets (~€30)
- Weipu SP13 connectors x4 sets (~€40)
- Cable glands PG7/PG9 pack (~€10)
- Marine wire 18AWG + 22AWG (~€20)

**Gate Test:**
Float the buoy for 24h in controlled conditions. All ocean-grade sensor data flowing to Obs Center via LoRa. Oil detection cycle running at night. Health monitoring active. No water ingress. Power system sustaining operations.

---

## 4. Dependency Graph

```
     M1 (Dev Sensors)─────────────────────┐
     Can start NOW                        │
          │                               │
          │                               ▼
     M2 (Health)                    M4 (Oil Detection)
     Can start NOW                  Needs M1 + M3
          │                               │
          │                               │
   M2.5 (LoRa Tool)                      │
   Can start NOW                          │
          │                               │
          ▼                               │
     M3 (LoRa Chain)                     │
     Needs M2.5                           │
          │                               │
          ▼                               ▼
     M5 (Power) ◄──── Needs M1 + M2 (real power measurements)
          │
          ▼
     M6 (Ocean-Grade Sensors) ◄─── Needs M1 proven + M4 pipeline working
          │
          ▼
     M7 (Integration) ◄─── Needs ALL
```

### Parallel Work Opportunities

| Time Period | Can Work Simultaneously |
|-------------|----------------------|
| **Now** | M1 (Dev Sensors) + M2 (Health) + M2.5 (LoRa Tool) |
| **After M2.5** | M3 (LoRa Chain) -- while M1/M2 continue |
| **After M1 + M3** | M4 (Oil Detection) |
| **After M1 + M2** | M5 (Power) -- can overlap with M4 |
| **After M4** | M6 (Ocean-Grade Sensor Upgrade) |
| **After ALL** | M7 (Integration & Enclosure) |

---

## 5. Procurement Alignment

### Wave 1: Order Now (needed for M1, M2, M2.5)

| Item | For | Est. Cost |
|------|-----|-----------|
| Dallas DS18B20 temp sensor | M1 | ~€3 |
| Cheap pH sensor module | M1 | ~€12 |
| 4.7kΩ resistor (DS18B20 pull-up) | M1 | ~€0.10 |
| Internal sensors (temp/humidity) | M2 | TBD (lab stock?) |
| (TDS sensor already in lab) | M1 | €0 |
| (LoRa boards already in lab) | M2.5 | €0 |

**Wave 1 Total: ~€15** (most hardware already available)

### Wave 2: Order After M1/M2 Validated (needed for M3, M4)

| Item | For | Est. Cost |
|------|-----|-----------|
| Pi Zero 2W + LoRa module | M3 | ~€50 |
| HC-SR501 PIR x2 | M4 | €4 |
| JSN-SR04T ultrasonic | M4 | €8 |
| NE555 + 30A relay + components | M4 | €15 |
| Warning strobe lamp | M4 | €15 |
| Green Cell inverter 150W | M4 | €40 |
| UV LEDs 10W 365nm x4 | M4 | €60 |
| DFRobot IMX378 camera | M4 | €39 |

**Wave 2 Total: ~€231**

### Wave 3: Order After M4 Validated (needed for M5)

| Item | For | Est. Cost |
|------|-----|-----------|
| LiFePO4 50Ah battery | M5 | €154 |
| Victron MPPT 75/15 | M5 | €72 |
| Solar panels 60W x2 | M5 | €98 |
| DC-DC converters x2 | M5 | €30 |
| Marine fuse block | M5 | €15 |

**Wave 3 Total: ~€369**

### Wave 4: Order When Pipeline Proven (needed for M6)

| Item | For | Est. Cost |
|------|-----|-----------|
| Atlas Conductivity Kit K 1.0 | M6 | €253 |
| Atlas Dissolved Oxygen Kit | M6 | €390 |
| Blue Robotics Bar30 | M6 | €99 |
| RS485-to-TTL modules x3 | M6 | €6 |

**Wave 4 Total: ~€748** (the big investment, only after system is proven)

### Wave 5: Order After M6 Validated (needed for M7)

| Item | For | Est. Cost |
|------|-----|-----------|
| Buoy frame (replacement) | M7 | TBD |
| Weipu connectors | M7 | €70 |
| Cable glands + marine wire | M7 | €30 |

**Wave 5 Total: ~€100 + frame**

**Grand Total (excluding buoy frame): ~€1,463**

> **Key Advantage:** You only spend ~€15 to get M1+M2+M2.5 running. The €748 ocean-grade
> sensor investment is deferred until Wave 4, when the entire system pipeline is proven.
> This de-risks the project significantly.

---

## 6. Spec Writing Priority

Specs should be written just-in-time, not all at once. Order:

| Priority | Spec | Write When | Needed By |
|----------|------|-----------|-----------|
| 1 | **SPEC-005** (Dev Sensor Platform) | **Now** | M1 |
| 1 | **SPEC-006** (Health Circuit) | **Now** | M2 |
| 1 | **SPEC-007** (LoRa Configurator) | **Now** | M2.5 |
| 2 | SPEC-008 (LoRa Chain) | When M2.5 nears completion | M3 |
| 3 | SPEC-009 (Oil Detection) | When M1 + M3 validated | M4 |
| 4 | SPEC-010 (Power) | When M1 + M2 validated | M5 |
| 5 | SPEC-011 (Ocean-Grade Sensors) | When pipeline proven | M6 |
| 6 | SPEC-012 (Integration) | When all systems validated | M7 |

---

## 7. Success = SPEC-000 Complete

When M7 passes its gate test, all SPEC-000 Section 10 (Success Criteria) checkboxes should be checked. That is Phase 1 complete.

---

## 8. Amendments

This roadmap may be amended as hardware realities, procurement timelines, or priorities change. All amendments logged to ADS with `spec_ref: SPEC-004`.

---

*This is the table of contents. The chapters come next.*
