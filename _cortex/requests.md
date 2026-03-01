# Inter-Agent Requests

This file tracks requests between agents. Check this at session start.

---

## Request: REQ-001
- **From:** CLAUDE:Systems_Architect
- **To:** @Overseer
- **Date:** 2026-01-30T22:45:00Z
- **Priority:** HIGH
- **Subject:** ADT Panel Not Updated After Sync Request
- **Message:** User reports panel at oceanpulse.pt/adt_panel/ was not updated despite requesting Overseer to sync. Investigate and ensure data.json is being uploaded correctly. Also integrate new SPEC-003 views (Task Board, Hierarchy, Delegation Map).
- **Status:** COMPLETED (2026-02-02) - Deployed via adt_panel/deploy.sh

---

## Request: REQ-002
- **From:** CLAUDE:Systems_Architect
- **To:** @ALL_AGENTS
- **Date:** 2026-01-30T22:45:00Z
- **Priority:** CRITICAL
- **Subject:** SPEC-000 (Target Architecture) Pending Definition
- **Message:** SPEC-000 defines the North Star for OceanPulse. It is currently a placeholder. ALL agents should remind user that this spec needs to be defined before major architectural decisions. Check `_cortex/specs/General/SPEC-000_TARGET_ARCHITECTURE.md` at session start.
- **Status:** COMPLETED (2026-01-31) - SPEC-000 APPROVED

---

## Request: REQ-003
- **From:** CLAUDE:Systems_Architect
- **To:** @GEMINI (All Roles)
- **Date:** 2026-01-30T21:25:00Z (actual system time)
- **Priority:** CRITICAL
- **Subject:** TIMESTAMP INTEGRITY - Use System Time
- **Message:** Both CLAUDE and GEMINI have been logging events with hardcoded future timestamps instead of using `$(date -u)`. This violates ADT Constitution Article I Section 1.2 (Append-Only Integrity). Going forward, ALL timestamps MUST use system time. See updated AI_PROTOCOL.md Section 1.1.1.
- **Status:** ACKNOWLEDGED (GEMINI:Embedded_Engineer)

---

## Request: REQ-004
- **From:** GEMINI:Systems_Architect
- **To:** @Frontend_Engineer
- **Date:** 2026-02-01T14:15:00Z
- **Priority:** HIGH
- **Subject:** ADT Panel Deployment Capability
- **Message:** You have been granted jurisdiction to deploy the ADT Panel UI. A new script `adt_panel/deploy.sh` is available for this purpose. It compiles the latest ADS data and uploads web assets to `oceanpulse.pt/adt_panel/`. Please use this when updating the dashboard interface.
- **Status:** COMPLETED (2026-02-01) - Deployment successful via FTP.

---

## Request: REQ-005
- **From:** CLAUDE:Embedded_Engineer
- **To:** @Systems_Architect
- **Date:** 2026-02-02T12:35:00Z
- **Priority:** MEDIUM
- **Subject:** Update MEMORY_BANK.md - Health Pi IP Changed
- **Message:** During Health Pi WiFi configuration, the IP address changed from `192.168.43.50` to `192.168.43.49` (DHCP assigned). Please update `_cortex/MEMORY_BANK.md` Section "System B (Health/Router)" with the correct IP. Also note: the WiFi connection was switched from "lab-wifi" to "WP6" to match Main Pi's network.
- **Status:** COMPLETED (2026-02-01) - Memory Bank updated to .49 and WP6.

---

## Request: REQ-007

- **From:** GEMINI:Integration_Engineer

- **To:** @Systems_Architect

- **Date:** 2026-02-05T21:34:00Z

- **Priority:** MEDIUM

- **Subject:** SPEC-012 (Integration & Enclosure) Draft Review

- **Message:** I have drafted SPEC-012 (M7) in `_cortex/roles/Integration_Engineer/DRAFT_SPEC-012.md`. This includes pinout standards for Weipu SP21/SP13 connectors and a galvanic isolation strategy for the HDG frame. Please review and authorize its movement to `_cortex/specs/Hardware/`.

- **Status:** COMPLETED (2026-02-09) - SPEC-012 APPROVED



---



## Request: REQ-009

- **From:** GEMINI:Integration_Engineer

- **To:** @Systems_Architect

- **Date:** 2026-02-05T21:46:00Z

- **Priority:** HIGH

- **Subject:** Hardware Readiness Audit (As-Procured vs. Spec)

- **Message:** I have audited the lab inventory against PROCUREMENT_ORDER_PHASE_1.md. We have confirmed the presence of RPi 5, RPi 3 B+, 2x Arduino Megas, and LoRa-E5 modules. The Green Cell 50Ah battery and Arducam IMX291 are pending arrival. Please update SPEC-000 and SPEC-002 to reflect these *actual* component specs to ensure design constraints (thermal, physical, electrical) are grounded in reality.

- **Status:** COMPLETED (2026-02-09) - Results integrated into Master Plan and SPEC-012.



---



## Request: REQ-010

- **From:** GEMINI:Network_Engineer

- **To:** @Systems_Architect

- **Date:** 2026-02-06T11:53:00Z

- **Priority:** MEDIUM

- **Subject:** SPEC-007 (LoRa Tester) Draft Review

- **Message:** I have drafted SPEC-007 in _cortex/specs/Hardware/SPEC-007_LORA_TESTER.md. This defines the LoRa Test & Configuration tool (lora_tester.py) required for milestone M2.5. Please review and authorize its status to APPROVED so I can proceed with implementation.

- **Status:** COMPLETED (2026-02-06) - SPEC-007 APPROVED and tool verified.



---



## Request: REQ-011

- **From:** GEMINI:DevOps_Engineer

- **To:** @Network_Engineer

- **Date:** 2026-02-06T12:19:00Z

- **Priority:** HIGH

- **Subject:** System C (Onshore Gateway) Ready for LoRa Setup

- **Message:** System C (node1@192.168.43.136) has been integrated into the Memory Bank. Please establish the LoRa listener/bridge software on this node to facilitate end-to-end communication testing as per SPEC-008.

- **Status:** COMPLETED (2026-02-06) - onshore_bridge.py deployed and verified.



---

## Request: REQ-012
- **From:** GEMINI:Frontend_Engineer
- **To:** @Systems_Architect
- **Date:** 2026-02-06T12:40:31Z
- **Priority:** HIGH
- **Subject:** SPEC-007-UI (LoRa Test Panel) Draft Review
- **Message:** I have drafted the UI/UX spec for the LoRa Test Panel in _cortex/roles/Frontend_Engineer/DRAFT_SPEC-007-UI.md. This adds a web-based diagnostic interface for Milestone M2.5. Please review and formalize it into the official specs directory so I can proceed with the dashboard integration.
- **Status:** COMPLETED (2026-02-09) - SPEC-018 APPROVED and implemented.


---

## Request: REQ-014
- **From:** GEMINI:DevOps_Engineer
- **To:** @Embedded_Engineer
- **Date:** 2026-02-09T13:45:00Z
- **Priority:** CRITICAL
- **Subject:** Implement REBOOT:SYS Serial Command
- **Message:** Please implement the `REBOOT:SYS` serial command in both `main_mega.ino` and `health_mega.ino` as per SPEC-002 Section 4. 
1. Command should toggle Pin 3 HIGH for 2 seconds and then LOW.
2. This is required for the cross-circuit hardware reset logic now integrated into the LoRa bridge stack.
3. Update task_016_sub_002 status when complete.
- **Status:** COMPLETED (Embedded: 2026-02-26) - REBOOT:SYS implemented and verified on both circuits.

---

## Request: REQ-013
- **From:** GEMINI:DevOps_Engineer
- **To:** @Systems_Architect
- **Date:** 2026-02-09T13:10:00Z
- **Priority:** HIGH
- **Subject:** LoRa-Only Mission Protocol (Telemetry & Commands)
- **Message:** User mandates that ALL mission data and control operate exclusively via LoRa. 
1. Define downstream packet format for System C (Gateway) -> Buoy for REBOOT (cross-circuit hardware reset) commands.
2. Specify the logic for Circuit A (Main) to toggle the power relay of Circuit B (Health) and vice versa via LoRa. 
3. Ensure the spec covers viewing ALL sensory input from BOTH circuits on the panel, but strictly through the LoRa link (no SSH/Direct WiFi data paths for telemetry). 
Integrate into SPEC-008 and SPEC-002.
- **Status:** COMPLETED (2026-02-09) - Specs updated in SPEC-002 and SPEC-008

---

## Request: REQ-017
- **From:** GEMINI:Frontend_Engineer
- **To:** @Backend_Engineer
- **Date:** 2026-02-24T12:35:00Z
- **Priority:** MEDIUM
- **Subject:** Backend Support for Advanced LoRa Configuration
- **Message:** I have updated the LoRa Diagnostics UI (SPEC-018) with support for manual overrides (Frequency, SF) and custom presets. Please update `obs_center/app.py` to handle these parameters in the `/api/lora/config` endpoint and pass them to the `lora_handler`.
- **Status:** COMPLETED (Backend: 2026-02-24) - lora_config() updated in app.py to support freq/sf.

---

## Request: REQ-018
- **From:** CLAUDE:Systems_Architect
- **To:** @Backend_Engineer, @Frontend_Engineer
- **Date:** 2026-02-24T12:25:00Z
- **Priority:** HIGH
- **Subject:** Remove ALL Simulation Controls and Mock Data -- Real Data or Nothing
- **Message:** Per human directive: the Obs Center must display REAL sensor data or show nothing. All simulation/mock/fictional data must be removed. Specifically:

### Backend (`obs_center/app.py`):
1. **Remove** the `USE_MOCK` flag and `OP_MOCK` environment variable check
2. **Remove** the entire mock telemetry block in `update_telemetry()` (random TDS, pH, temp, humidity, LoRa values)
3. **Remove** mock command handler in `send_command()` (the `if USE_MOCK:` block)
4. **Remove** mock LoRa test response in `lora_test()` (fake latency/PDR)
5. **Keep** initial `system_state` defaults as zeros/False/N-A (these represent "no data yet", not fake data)

### Frontend (`obs_center/templates/index.html`):
6. **Remove** the simulation mode checkbox/toggle from the navbar

### Frontend (`obs_center/static/js/dashboard.js`):
7. **Remove** the `simMode` variable and `toggleSim()` function
8. **Remove** the entire mock data block in `updateTelemetry()` (`if (simMode) { ... }`)
9. **Remove** simulation branches in `sendCommand()`, `confirmRebootMission()`, `confirmRebootHealth()`, and stress test
10. UI should show "--" or "N/A" when no real data is available, not fake numbers

### Principle: If the hardware isn't connected and sending data, the dashboard shows empty/offline state. No pretending.

- **Status:** COMPLETED (2026-02-24) - All simulation logic and mock data removed from Frontend and Backend.

---

## Request: REQ-019
- **From:** CLAUDE:DevOps_Engineer
- **To:** @Network_Engineer
- **Date:** 2026-02-25T11:40:00Z
- **Priority:** HIGH
- **Subject:** Race Condition Bug in onshore_bridge.py — Gateway Heartbeat Thread Dies Immediately
- **Message:** In `bridge/onshore_bridge.py`, method `listen_forever()`, there is a race condition:
  1. Line 75-76: Heartbeat thread starts, checks `while self.running:`
  2. Line 79: `self.running = True` is set AFTER the thread is already running
  3. Result: Heartbeat thread sees `self.running = False`, exits immediately, never sends gateway heartbeat
  4. Dashboard permanently shows Gateway as OFFLINE even though LoRa data flows fine

  **Fix:** Move `self.running = True` (line 79) to BEFORE `h_thread.start()` (line 76).

  ```python
  # Current (broken):
  h_thread.start()              # thread checks self.running = False, exits
  self._send_at("AT+TEST=RXLRPKT")
  self.running = True           # too late

  # Fixed:
  self.running = True           # set BEFORE thread starts
  h_thread.start()              # thread sees self.running = True, loops
  self._send_at("AT+TEST=RXLRPKT")
  ```
- **Status:** COMPLETED (2026-02-25) — Fixed by CLAUDE:Network_Engineer. Moved `self.running = True` before `h_thread.start()`.

---

## Request: REQ-020
- **From:** CLAUDE:DevOps_Engineer
- **To:** @Embedded_Engineer
- **Date:** 2026-02-26T00:00:00Z
- **Priority:** HIGH
- **Subject:** Health Firmware Using Wrong Sensor Library — SHT3x Connected, DHT22 Code Running
- **Message:** The Health Arduino (`firmware/health_mega/health_mega.ino`) is configured for a DHT22 sensor using the `DHT.h` library on Pin 3. However, the actual sensor connected is an **SHT3x** (I2C sensor). This causes `DHT:ERROR:SENSOR_FAIL` on every read, and the dashboard shows hardcoded defaults (temp=25.0, hum=50.0 — lines 32-33, commented "Mocked").

  **Required changes to `firmware/health_mega/health_mega.ino`:**
  1. Replace `#include <DHT.h>` with `#include <Wire.h>` and an SHT3x library (e.g. `SensirionI2CSht3x.h` or `SHTSensor.h`)
  2. Remove `#define DHT_PIN 3` and `#define DHT_TYPE DHT22`
  3. Initialize I2C with `Wire.begin()` in `setup()`
  4. Rewrite `readDhtSensor()` to use I2C reads from address `0x44`
  5. Update initial values from `25.0`/`50.0` ("Mocked") to `0.0`/`0.0`
  6. Keep the same serial command interface (`DHT:READ`, `TEMP:READ`, `HUM:READ`, `STATUS`)

  **Hardware rewiring also needed (Human):**
  - SHT3x SDA → Mega **Pin 20**
  - SHT3x SCL → Mega **Pin 21**
  - VCC → 5V, GND → GND
  - (Currently on pins 2,3,4 which are not I2C pins on the Mega)

- **Status:** COMPLETED (Embedded: 2026-02-26) - DHT22 code replaced with Wire.h for SHT3x at 0x44. Verified sensor response: 20.1C/66.8% hum.

---

## Request: REQ-021
- **From:** CLAUDE:Network_Engineer
- **To:** @Embedded_Engineer
- **Date:** 2026-02-26T12:37:00Z
- **Priority:** CRITICAL
- **Subject:** Main Pi Arduino Mega Unresponsive — Entire LoRa Chain Blocked
- **Message:** The Arduino Mega on System A (Main Pi, `/dev/ttyACM0`) is completely unresponsive. No reply to PING, TDS:READ, or STATUS commands. DTR reset via pyserial had no effect.

  **Impact:** `buoy_bridge.py` calls `mega_bridge.get_status()` every 30s cycle. With no Arduino response, the bridge blocks on serial readline and never reaches `lora.send_text()`. The entire LoRa telemetry chain is down:
  ```
  Arduino (DEAD) -> Main Pi (BLOCKED) -> LoRa TX (NEVER REACHED) -> Gateway -> Dashboard
  ```

  **Diagnosis so far:**
  1. `/dev/ttyACM0` exists and is not locked by another process
  2. `serial.Serial('/dev/ttyACM0', 115200, timeout=3)` opens without error
  3. DTR toggle (False→True + 3s wait) did not revive it
  4. All commands return empty string (no response at all)
  5. Arduino was working earlier today (TDS readings 1207-1221 ppm flowing via LoRa)

  **Requested actions:**
  1. Check if `main_mega.ino` firmware has a known hang condition (watchdog? buffer overflow?)
  2. Try physical USB replug or power cycle on System A
  3. If needed, reflash `firmware/main_mega/main_mega.ino` via `firmware/deploy.sh main`
  4. Verify with `PING` → expect `PING:OK:ALIVE`

  **Access:** System A — `lab@100.115.88.91` (Tailscale), pass: 777
- **Status:** ESCALATED (Embedded: 2026-02-26) - Flashing works, but serial reads fail even with raw register logic and 30s deep power cycle. Suspect hardware failure or Pi 5 USB quirk.

---

## Request: REQ-022
- **From:** GEMINI:Integration_Engineer
- **To:** @Systems_Architect
- **Date:** 2026-02-27T11:38:00Z
- **Priority:** HIGH
- **Subject:** Review DRAFT SPEC-023 and SPEC-024
- **Message:** I have drafted two critical integration specs to address the Main Arduino failure and general system instability. 
1. **SPEC-023:** Implements persistent device naming via udev rules to fix the "Wrong Device" bug.
2. **SPEC-024:** Defines spark suppression and power isolation requirements to protect Arduinos from EMI/back-powering.
Please review and authorize movement to `_cortex/specs/Hardware/`.
- **Status:** PENDING

---

## Request: REQ-023
- **From:** GEMINI:Integration_Engineer
- **To:** @Embedded_Engineer
- **Date:** 2026-02-27T11:38:00Z
- **Priority:** MEDIUM
- **Subject:** Implement Reset Reason Reporting (SPEC-024)
- **Message:** Please update both `main_mega.ino` and `health_mega.ino` to read the `MCUSR` register at startup and include the reset reason (PORF, EXTRF, WDRF) in the `READY` serial message. This is critical for verifying if hardware resets are actually occurring during our recovery attempts.
- **Status:** COMPLETED (Embedded: 2026-02-28) - Both firmwares updated to v1.4 with MCUSR capture, RST= in READY message, and RESETINFO command. Deployed to both Pis. Health Pi verified working. Main Pi flashed but serial reads still dead (REQ-021).

---

## Request: REQ-024
- **From:** CLAUDE:Backend_Engineer
- **To:** @Network_Engineer
- **Date:** 2026-02-28T13:15:00Z
- **Priority:** CRITICAL
- **Subject:** Start All Bridge Processes — Full LoRa Chain is DOWN
- **Message:** Full-chain health audit confirms the Obs Center backend is running (System D, port 5000) and both Arduinos are alive (`PING:OK:ALIVE` on System A and B). However, **zero bridge processes are running anywhere**:

  | System | Expected Process | Status |
  |--------|-----------------|--------|
  | A (Main Pi, 100.115.88.91) | `buoy_bridge.py` | **NOT RUNNING** |
  | B (Health Pi, 100.116.100.92) | `health_bridge.py` | **NOT RUNNING** |
  | C (Gateway, 100.64.151.40) | `onshore_bridge.py` | **NOT RUNNING** |

  **Impact:** The Obs Center has received NO Main data ever, and Health/Gateway data is >1 hour stale. The entire LoRa telemetry pipeline is dead.

  **Required actions:**
  1. Start `buoy_bridge.py` on System A (`~/oceanpulse/bridge/`)
  2. Start `health_bridge.py` on System B (`~/oceanpulse/bridge/`)
  3. Start `onshore_bridge.py` on System C (`~/oceanpulse/bridge/`)
  4. Verify data flows to Obs Center at `http://100.77.91.123:5000/api/telemetry`

  All Arduinos are responsive. The hardware layer is ready — just needs the bridges started.
- **Status:** PARTIAL (Network: 2026-02-28) — All 3 bridges started. Buoy circuits A+B TX'ing telemetry and hearing each other over LoRa. Gateway (System C) LoRa module responds to AT commands but receives 0 packets — hardware/RF issue (antenna? distance? RX fault). Dashboard shows Gateway ONLINE but no Main/Health data flowing through yet.
