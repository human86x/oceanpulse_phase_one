# DRAFT SPEC-007-UI: LoRa Test Panel

**Status:** DRAFT
**Role:** Frontend_Engineer
**References:** SPEC-007 (LoRa Tester), SPEC-001 (OpsCenter)

---

## 1. Overview
The LoRa Test Panel is a specialized module within the Observational Center UI designed to visualize radio link performance and tune modem parameters in real-time.

---

## 2. UI Components

### 2.1 Radio Signal Gauges (Real-Time)
- **RSSI Gauge:** -140dBm to -20dBm range. Color-coded (Red: <-120, Yellow: -120 to -90, Green: >-90).
- **SNR Gauge:** -20dB to +15dB range.
- **Link Quality Index (LQI):** A percentage-based derived metric based on RSSI/SNR and PDR.

### 2.2 Signal Stability Chart
- A multi-line Chart.js graph showing RSSI and SNR over the last 5 minutes.
- Purpose: Detect interference or environmental fading.

### 2.3 Configuration Console
- **Modem Preset Selector:** Dropdown for Meshtastic presets (Short/Fast, Long/Slow, etc.).
- **Manual Overrides:** (Advanced Mode) Frequency, Bandwidth, Spreading Factor.
- **Set Region:** Dropdown for regulatory regions (EU_868, etc.).

### 2.4 Diagnostic Tests
- **Ping Button:** Triggers an atomic RTT test. Displays result in a "Latency" badge.
- **PDR Stress Test:** Input for `N` packets. Progress bar shows completion. Result displays as `X/N Delivered (Y%)`.

---

## 3. Implementation Logic

### 3.1 Backend Bridge
The panel will communicate with `obs_center/app.py` via:
- `GET /api/lora/metrics`: Returns current signal metadata.
- `POST /api/lora/config`: Sends new radio parameters.
- `POST /api/lora/test`: Triggers ping/stress modes.

### 3.2 Integration
The panel will reside in a new Tab in `index.html` labeled "**LoRa Diagnostics**".

---

## 4. Next Steps
1. Request **Systems_Architect** review and official spec number assignment.
2. Coordinate with **Network_Engineer** to ensure `lora_tester.py` outputs JSON compatible with the Web UI.
