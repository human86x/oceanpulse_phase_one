# SPEC-000: OceanPulse Target Architecture

**Status:** APPROVED
**Priority:** CRITICAL
**Owner:** Human + Systems_Architect
**Last Updated:** 2026-01-31

---

## 1. Mission Statement

**Primary Goal (Phase 1):** Detect and monitor **oil spill danger in the port**.

**Strategic Vision:** OceanPulse is a **multipurpose marine monitoring platform** designed as a proof-of-concept that can pivot to serve multiple markets:

| Direction | Partner | Use Case |
|-----------|---------|----------|
| **SAR (Search & Rescue)** | Bombeiros / Finisterra | Emergency response, coastal monitoring |
| **Environmental** | Local Council | Water quality, pollution detection |
| **Commercial** | Aquaculture businesses | Open sea cultivation monitoring |

> *"If the system works perfectly, we can demonstrate it to stakeholders and pivot to the direction with the best opportunity."*

---

## 2. Buoy Physical Architecture

### 2.1 Above Water (Watertight Case on Top)
| Component | Model | Specs |
|-----------|-------|-------|
| Camera | DFRobot IMX378 | 190° fisheye, high precision |
| UV Light | Everbeam 50W 365nm | AC (220V) |
| Environmental Sensors | [TBD] | Light, temp, etc. |

### 2.2 Internal (Inside Buoy Hull)
| Component | Model/Description |
|-----------|-------------------|
| UV Unit | Everbeam 50W 365nm UV (AC 230V) |
| Inverter | Green Cell Modified Sine Wave 12V DC → 230V AC 150W |
| Main Processing Unit | Raspberry Pi ("main") |
| Sensor Controller | Arduino Mega |
| Power System | See Section 4 |

### 2.3 Above-Water Sensors & Safety (Watertight Case)
| Component | Model | Qty | Purpose |
|-----------|-------|-----|---------|
| Ultrasonic | JSN-SR04T | 1 | **Proximity Veto** - abort UV if object <1.5m |
| PIR Motion | HC-SR501 | 2 | **Thermal Check** - hard lock UV if human detected |
| Warning Strobe | Yellow/Red waterproof lamp | 1 | **Visual Warning** - Arduino-triggered, 2 sec before UV |
| Hard-Stop Timer | NE555 + 30A Relay | 1 | **Hardware Cutoff** - max 500ms UV pulse |

### 2.3 Underwater (Submerged Sensors) - Phase 1

| Sensor | Model | Maintenance | Measures |
|--------|-------|-------------|----------|
| Temperature & Salinity | Atlas Scientific EZO™ ES Kit | Low/Medium | Temp, EC/Salinity |
| Pressure/Depth | Blue Robotics Bar30 | Low (stable) | Depth, pressure |
| Dissolved Oxygen | Atlas Scientific EZO™ DO Kit | Medium | DO levels |

> **Phase 1 Scope:** These 3 sensor systems only. Additional sensors in future phases.

### 2.4 Dual-Circuit Architecture

The buoy contains **TWO independent processing circuits** for redundancy and self-healing:

| Circuit | Components | Purpose |
|---------|------------|---------|
| **MAIN** | Pi + Arduino Mega | Sensors, UV, camera, primary LoRa |
| **HEALTH** | Pi + Arduino Mega | Internal monitoring, backup LoRa, watchdog |

**Interconnection:** Short LAN cable between Main Pi ↔ Health Pi

**Failsafe Mechanism:** Each circuit has a relay to power-cycle the other:
- If Main freezes → Obs Center commands Health circuit via backup LoRa → Health relay restarts Main
- If Health freezes → Main circuit can restart Health

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                              BUOY HULL                                        │
│  ┌─────────────────────────────┐      ┌─────────────────────────────┐        │
│  │      MAIN CIRCUIT           │      │      HEALTH CIRCUIT         │        │
│  │  ┌─────────────────────┐    │ LAN  │    ┌─────────────────────┐  │        │
│  │  │ Raspberry Pi (main) │◄───┼──────┼───►│ Raspberry Pi (health)│  │        │
│  │  └─────────────────────┘    │      │    └─────────────────────┘  │        │
│  │  ┌─────────────────────┐    │      │    ┌─────────────────────┐  │        │
│  │  │ Arduino Mega        │    │      │    │ Arduino Mega        │  │        │
│  │  └─────────────────────┘    │      │    └─────────────────────┘  │        │
│  │  ┌─────────────────────┐    │      │    ┌─────────────────────┐  │        │
│  │  │ LoRa (Primary)      │    │      │    │ LoRa (Backup)       │  │        │
│  │  └─────────────────────┘    │      │    └─────────────────────┘  │        │
│  │  ┌─────────────────────┐    │      │    ┌─────────────────────┐  │        │
│  │  │ RELAY → Health pwr  │    │      │    │ RELAY → Main pwr    │  │        │
│  │  └─────────────────────┘    │      │    └─────────────────────┘  │        │
│  │                             │      │                             │        │
│  │  Sensors: TDS, DO, Temp,    │      │    Monitors:                │        │
│  │  Salinity, Pressure/Depth   │      │    - Internal temperatures  │        │
│  │  Controls: UV, Camera       │      │    - Humidity               │        │
│  └─────────────────────────────┘      │    - Voltage levels         │        │
│                                       └─────────────────────────────┘        │
│  ┌───────────────────────────────────────────────────────────────┐           │
│  │ POWER: LiFePO4 50Ah + Victron MPPT 75/15 + 100W Solar         │           │
│  └───────────────────────────────────────────────────────────────┘           │
└──────────────────────────────────────────────────────────────────────────────┘
                             │
    ~~~~~~~~~~~~~~~~~~~~~~~~│~~~~ WATER LINE ~~~~
                             │
                    ┌────────┴────────────┐
                    │  UNDERWATER PROBES  │
                    │  - Atlas EZO ES     │
                    │  - Atlas EZO DO     │
                    │  - Bar30 Pressure   │
                    └─────────────────────┘
```

---

## 3. Communication Architecture (Phase 1)

### Dual-Path LoRa (Redundancy)

```
┌─────────────────────────────────────┐
│              BUOY                   │
│  ┌────────────┐   ┌────────────┐   │
│  │ MAIN LoRa  │   │HEALTH LoRa │   │
│  │ (Primary)  │   │ (Backup)   │   │
│  └─────┬──────┘   └─────┬──────┘   │
└────────┼────────────────┼──────────┘
         │                │
         │    LoRa        │  LoRa (if Main down)
         ▼                ▼
┌─────────────────────────────────────┐         WiFi         ┌─────────────────────┐
│        ONSHORE GATEWAY              │ ───────────────────► │ OBSERVATIONAL CENTER│
│                                     │                      │                     │
│  Pi Zero 2W + LoRa Wemo Mini        │                      │ obs_center (webapp) │
│  USB Charger                        │                      │                     │
└─────────────────────────────────────┘                      └─────────────────────┘
```

### Communication Paths

| Path | Source | Destination | Protocol | Purpose |
|------|--------|-------------|----------|---------|
| **Primary** | Main Circuit | Onshore → Obs Center | LoRa → WiFi | Sensor data, commands |
| **Backup** | Health Circuit | Onshore → Obs Center | LoRa → WiFi | Health data, emergency restart |

### Onshore Gateway Hardware
| Component | Model |
|-----------|-------|
| Processing | Raspberry Pi Zero 2W |
| LoRa Module | Wemo Mini (LoRa) |
| Power | USB Charger device |

### Failsafe Scenario
```
Main Circuit Frozen:
1. Obs Center detects Main not responding
2. Obs Center sends restart command via Onshore
3. Onshore relays to Health Circuit (backup LoRa)
4. Health Circuit triggers relay → power-cycles Main
5. Main reboots and resumes operation
```

**Future phases:** [TBD - Mesh LoRa? Cellular? Satellite?]

---

## 4. Power System

| Component | Specification |
|-----------|---------------|
| Battery | Green Cell 50Ah LiFePO4 |
| Solar Panel | 100W Flexible Panel |
| Charge Controller | Victron MPPT 75/15 |

### Power Budget
| Consumer | Est. Draw | Notes |
|----------|-----------|-------|
| **MAIN CIRCUIT** | | |
| Raspberry Pi (main) | ~3-5W | Continuous |
| Arduino Mega (main) | ~0.5W | Continuous |
| LoRa Module (primary) | ~0.1W TX | Intermittent |
| UV Unit (Everbeam 50W) | ~50W when active | 5-10 min cycle intervals |
| Inverter (Green Cell 150W) | ~5-10W idle, 150W max | 12V→230V modified sine |
| Ultrasonic (JSN-SR04T) | ~0.1W | Intermittent |
| PIR Sensors (2x HC-SR501) | ~0.1W | Continuous |
| Camera (DFRobot IMX378) | ~2W | 190° fisheye |
| Sensors (Atlas + Bar30) | ~1W | Continuous |
| **HEALTH CIRCUIT** | | |
| Raspberry Pi (health) | ~3-5W | Continuous |
| Arduino Mega (health) | ~0.5W | Continuous |
| LoRa Module (backup) | ~0.1W TX | Intermittent |
| Internal sensors | ~0.5W | Temp, humidity, voltage |
| **TOTAL ESTIMATE** | ~12-15W | Continuous base load |

**Autonomy Target:** 2-3 days without sun (typical conditions provide regular solar input)

> **Note:** 50Ah @ 12V = 600Wh. At 15W continuous = ~40h theoretical. With solar input, 2-3 day target achievable.

---

## 5. Processing Architecture

### Main Circuit
| Device | Role |
|--------|------|
| Raspberry Pi ("main") | Central processing, primary LoRa, data logging, UV/camera control |
| Arduino Mega | Water quality sensor I/O, relay control, real-time tasks |

**Serial Protocol:** See SPEC-002

### Health Circuit
| Device | Role |
|--------|------|
| Raspberry Pi ("health") | Health monitoring, backup LoRa, watchdog |
| Arduino Mega | Internal sensors (temp, humidity, voltage), restart relay |

**Health Monitoring Targets:**
- Internal compartment temperatures (standard temp sensors - TBD)
- Humidity levels (standard humidity sensors - TBD)
- Voltage levels (read from Victron MPPT module)

**Inter-Circuit Communication:** LAN cable (Pi ↔ Pi) - protocol TBD (internal failover use)

---

## 6. Functional Requirements

### Main Circuit Functions
| Capability | Requirement | Status |
|------------|-------------|--------|
| Temperature & Salinity | Atlas Scientific EZO ES Kit | Phase 1 |
| Pressure/Depth | Blue Robotics Bar30 | Phase 1 |
| Dissolved Oxygen | Atlas Scientific EZO DO Kit | Phase 1 |
| UV Treatment | Continuous cycling operation | Phase 1 |
| Visual Monitoring | High-resolution camera (max precision) | Phase 1 |
| Remote Control | Relay actuation | Phase 1 |
| Data Transmission | Primary LoRa to shore | Phase 1 |
| Oil Detection | Primary mission - port safety | Phase 1 |

### Health Circuit Functions
| Capability | Requirement | Status |
|------------|-------------|--------|
| Internal Temp Monitoring | Multiple compartment zones | Phase 1 |
| Humidity Monitoring | Electronics protection | Phase 1 |
| Voltage Monitoring | Power system health | Phase 1 |
| Backup Communication | Independent LoRa link | Phase 1 |
| Watchdog/Restart | Power-cycle Main if frozen | Phase 1 |

### System-Wide
| Capability | Requirement | Status |
|------------|-------------|--------|
| Solar Charging | 2-3 day autonomy | Phase 1 |
| Dual-Circuit Redundancy | Self-healing capability | Phase 1 |

---

## 7. Environmental Requirements

| Parameter | Requirement | Standard |
|-----------|-------------|----------|
| Waterproofing | IP68 (Hull/Underwater), IP67 (Internal Box) | SPEC-012 |
| Operating Temp | -10°C to +55°C (Summer Port Operation) | SPEC-012 |
| Deployment | Continuous saltwater immersion (Sagres) | SPEC-012 |
| Wave/Weather | Standard Atlantic coastal conditions | SPEC-012 |
| **Ground Truth** | Tinned copper wiring, SS316 only, Galvanic isolation | SPEC-012 |

> **Grounding in Reality:** Following the 2026-02-05 Hardware Audit, all environmental
> mitigations (PIR humidity, Inverter EMI, pH drift) are standardized in SPEC-012.

---

## 8. Oil Detection System: Safe-Pulse Fluorescence Sentry

### 8.1 Detection Principle

OceanPulse uses **UV-A fluorescence** to detect hydrocarbons on the water surface:
- Oil/fuel residues **fluoresce bright white-blue** under 365nm UV light
- Clean water remains **optically dark** = extremely high contrast
- Can detect **very thin surface sheens** invisible to standard cameras
- **Night-time operation only** (controlled conditions)

### 8.2 Night Protocol

```
┌─────────────────────────────────────────────────────────────────┐
│                    DETECTION CYCLE                              │
│                                                                 │
│  1. Safety checks (PIR + Ultrasonic + clear zone)              │
│  2. Amber warning strobe (2 seconds)                           │
│  3. UV pulse fires (max 500ms, hardware-limited)               │
│  4. Camera shutter synchronized - freezes wave motion          │
│  5. Edge AI analyzes image locally                             │
│  6. If oil detected → transmit alert + compressed thumbnail    │
│                                                                 │
│  Cycle interval: 5-10 minutes                                  │
└─────────────────────────────────────────────────────────────────┘
```

- **UV Strobe:** Precisely timed 365nm pulse (NOT continuous)
- **Camera Sync:** High-speed shutter synchronized to UV pulse
- **Result:** Blur-free imagery even in dynamic port conditions

### 8.3 "Zero Harm" Triple-Lock Safety Interlock

**UV can ONLY fire when ALL conditions are met:**

```
┌─────────────────────────────────────────────────────────────────┐
│              TRIPLE-LOCK SAFETY ARCHITECTURE                    │
│                                                                 │
│  ┌─────────────┐   ┌─────────────┐   ┌─────────────┐           │
│  │ 1. THERMAL  │   │ 2. PROXIMITY│   │ 3. WARNING  │           │
│  │    CHECK    │   │    VETO     │   │    STROBE   │           │
│  │             │   │             │   │             │           │
│  │ PIR sensors │   │ Ultrasonic  │   │ Amber beacon│           │
│  │ (HC-SR501)  │   │ (JSN-SR04T) │   │ 2 sec before│           │
│  │             │   │             │   │             │           │
│  │ Human heat  │   │ Object in   │   │ Visual warn │           │
│  │ detected?   │   │ zone <1.5m? │   │ to personnel│           │
│  │     ↓       │   │     ↓       │   │     ↓       │           │
│  │ HARD LOCK   │   │ ABORT PULSE │   │ PROCEED     │           │
│  └─────────────┘   └─────────────┘   └─────────────┘           │
│                                                                 │
│  ┌─────────────────────────────────────────────────┐           │
│  │ 4. HARDWARE HARD-STOP (NE555 Timer Circuit)     │           │
│  │                                                  │           │
│  │ Independent circuit enforces MAX 500ms pulse    │           │
│  │ Prevents continuous exposure from software fault │           │
│  └─────────────────────────────────────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

| Lock | Sensor | Function | Failure Mode |
|------|--------|----------|--------------|
| **Thermal** | PIR (HC-SR501 x2) | Detect human heat in UV target zone | Hard lock UV |
| **Proximity** | Ultrasonic (JSN-SR04T) | Downward rangefinder, <1.5m abort | Abort pulse |
| **Warning** | Yellow/Red waterproof lamp | Arduino-triggered 2-sec warning | Mandatory delay |
| **Hard-Stop** | NE555 + 30A Relay | Hardware max 500ms pulse | Physical cutoff |

### NE555 Hardware Hard-Stop Circuit

```
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│   ARDUINO   │──ON──│   NE555     │──────│  30A RELAY  │──────│  INVERTER   │
│   (Main)    │      │   TIMER     │      │             │      │ Green Cell  │
│             │      │             │      │             │      │ 12V→230V    │
└─────────────┘      │ Max 500ms   │      │ Switches    │      │             │
                     │ pulse width │      │ inverter    │      └──────┬──────┘
                     └─────────────┘      │ power       │             │
                                          └─────────────┘             │ 230V AC
                                                                      ▼
                                                              ┌─────────────┐
                                                              │  UV STROBE  │
                                                              │ Everbeam    │
                                                              │ 50W 365nm   │
                                                              └─────────────┘

Flow:
1. Arduino sends ON signal
2. NE555 starts timing (max 500ms)
3. 30A relay closes → Inverter powered
4. UV strobe fires
5. NE555 times out → Relay opens → UV off
   (Even if Arduino signal stays high, NE555 cuts power)
```

### 8.4 Optical Safety (Fresnel Mitigation)

```
                         ▲ Reflected UV (~3%)
                         │ directed upward/away
                         │ from eye level
                        ╱
                       ╱
    ┌─────────────────╱────────────────┐
    │     UV EMITTER  ╲                │
    │                  ╲ 45° angle     │
    │                   ╲              │
    └────────────────────╲─────────────┘
                          ╲
                           ╲
    ~~~~~~~~~~~~~~~~~~~~~~~~╲~~~~~~ WATER SURFACE
                             ╲
                              ▼ ~97% absorbed by water

    Target Zone: ~7m² circular area beneath mast
```

### 8.5 Edge Intelligence

| Principle | Implementation |
|-----------|----------------|
| **Local Processing** | All image capture + analysis on-device |
| **No Raw Streaming** | Raw data never leaves the buoy |
| **Event-Driven TX** | Only confirmed oil events + thumbnails transmitted |
| **Network Independence** | Autonomous operation during connectivity loss |
| **Privacy by Design** | Minimizes data exposure |

### 8.6 Components Summary

| Component | Model | Role in Safety System |
|-----------|-------|----------------------|
| UV Strobe | Everbeam 50W 365nm | Fluorescence excitation |
| Camera | DFRobot IMX378 (190°) | Synchronized capture |
| PIR Sensors | HC-SR501 (x2) | Thermal check (human detection) |
| Ultrasonic | JSN-SR04T | Proximity veto (<1.5m abort) |
| Warning Strobe | [TBD - Amber beacon] | 2-sec pre-fire warning |
| Hard-Stop Timer | NE555 circuit | 500ms max pulse enforcement |
| Inverter | Green Cell 150W | 12V→230V for UV unit |

---

## 9. Data Architecture

### Edge Processing Model

```
┌─────────────────────────────────────────────────────────────────┐
│                         BUOY (Edge)                             │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │ Camera       │───►│ Local AI     │───►│ Decision     │      │
│  │ (IMX378)     │    │ Processing   │    │ Engine       │      │
│  └──────────────┘    └──────────────┘    └──────┬───────┘      │
│                                                  │               │
│                              ┌───────────────────┴────────┐     │
│                              │                            │     │
│                              ▼                            ▼     │
│                    ┌──────────────┐            ┌──────────────┐ │
│                    │ NO OIL       │            │ OIL DETECTED │ │
│                    │ Log locally  │            │ TX alert +   │ │
│                    │ No transmit  │            │ thumbnail    │ │
│                    └──────────────┘            └──────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                                                        │
                                                        │ LoRa
                                                        ▼
                                               ┌──────────────┐
                                               │   ONSHORE    │
                                               │   GATEWAY    │
                                               └──────────────┘
                                                        │ WiFi
                                                        ▼
                                               ┌──────────────┐
                                               │  OBS CENTER  │
                                               │  Dashboard   │
                                               │  Alerts      │
                                               └──────────────┘
```

---

## 10. Success Criteria

*OceanPulse Phase 1 is COMPLETE when:*

### Main Circuit
- [ ] Temperature/Salinity sensor (Atlas EZO ES) reporting to dashboard
- [ ] Pressure/Depth sensor (Bar30) reporting to dashboard
- [ ] Dissolved Oxygen sensor (Atlas EZO DO) reporting to dashboard
- [ ] UV unit cycling continuously under remote control
- [ ] Camera capturing high-res images
- [ ] Primary LoRa transmitting to onshore gateway

### Health Circuit
- [ ] Internal temperature monitoring (multiple zones) active
- [ ] Humidity monitoring active
- [ ] Voltage level monitoring active
- [ ] Backup LoRa link functional
- [ ] Remote restart of Main circuit works end-to-end

### Oil Detection System
- [ ] Triple-Lock Safety operational (PIR + Ultrasonic + Warning strobe)
- [ ] NE555 hardware hard-stop enforces 500ms max pulse
- [ ] UV/camera synchronization working
- [ ] Edge AI detecting oil fluorescence
- [ ] Event-driven alerts transmitting to Obs Center
- [ ] Fresnel mitigation verified (45° angle, 97% absorption)

### Integration
- [ ] Onshore gateway (Pi Zero 2W) relays both circuits to Obs Center
- [ ] Dashboard displays all sensor data (water quality + health + oil alerts)
- [ ] Remote control works for both circuits
- [ ] Solar charging maintains 2-3 day autonomy
- [ ] Failsafe restart tested and functional

---

## 11. Phase Mapping

| Phase | Scope | Delivers |
|-------|-------|----------|
| **Phase 1** | **1 Buoy (Dual-Circuit)** | Complete prototype with Main + Health circuits, 3 water quality sensors (Temp/Salinity, Pressure/Depth, DO), UV cycling, high-res camera, dual LoRa paths, health monitoring, self-healing restart, solar power |
| Phase 2 | [TBD] | Multi-buoy? Extended range? Partner integration? |
| Phase N | [TBD] | Scale deployment based on chosen market direction |

---

## 12. Market Strategy

```
                              ┌─────────────────────┐
                              │   PHASE 1 SUCCESS   │
                              │   (Proof of Concept)│
                              └──────────┬──────────┘
                                         │
              ┌──────────────────────────┼──────────────────────────┐
              ▼                          ▼                          ▼
    ┌─────────────────┐        ┌─────────────────┐        ┌─────────────────┐
    │   SAR DIRECTION │        │  ENVIRONMENTAL  │        │   COMMERCIAL    │
    │                 │        │                 │        │                 │
    │ Partner:        │        │ Partner:        │        │ Partner:        │
    │ Bombeiros       │        │ Local Council   │        │ Aquaculture     │
    │ Finisterra      │        │                 │        │ Businesses      │
    │                 │        │                 │        │                 │
    │ Focus:          │        │ Focus:          │        │ Focus:          │
    │ Search & Rescue │        │ Pollution       │        │ Open sea        │
    │ Coastal safety  │        │ Water quality   │        │ Cultivation     │
    └─────────────────┘        └─────────────────┘        └─────────────────┘
```

---

## Open Questions

### Resolved
1. ~~**Water quality sensors**~~ - Atlas EZO ES, Bar30, Atlas EZO DO
2. ~~**Camera model**~~ - DFRobot IMX378 (190° fisheye)
3. ~~**UV unit specs**~~ - Everbeam 50W 365nm UV (AC 230V)
4. ~~**Inverter model**~~ - Green Cell Modified Sine Wave 150W 12V→230V
5. ~~**UV cycle timing**~~ - 5-10 minute intervals, 500ms max pulse
6. ~~**Ultrasonic purpose**~~ - **Proximity Veto** for UV safety (<1.5m abort)
7. ~~**PIR purpose**~~ - **Thermal Check** for UV safety (human detection → hard lock)
8. ~~**Oil detection method**~~ - Safe-Pulse Fluorescence with Triple-Lock Safety

### Pending
11. **Health sensor models** - Standard temp/humidity sensors (TBD from lab)
12. **LAN protocol** - Not defined yet (internal communication, failover use)

### Resolved (This Session)
9. ~~**Warning strobe**~~ - Any yellow/red waterproof lamp, Arduino-triggered
10. ~~**NE555 circuit**~~ - NE555 timer → 30A relay → Inverter → UV strobe (500ms max)

> **Note:** 2x PIR sensors cover UV target zone only (not 360°). 3rd PIR in docs was dev backup.

---

*This spec is the primary reference for all development decisions.*
