# SPEC-007: LoRa Test & Configuration Tool

**Status:** DRAFT
**Priority:** HIGH
**Owner:** Network_Engineer
**Created:** 2026-02-06
**References:** SPEC-000, SPEC-004 (Milestone M2.5)

---

## 1. Purpose

Define the requirements and implementation for a LoRa testing and configuration tool to optimize the radio link between the buoy and onshore gateway using Meshtastic firmware on Seeed LoRa-E5 modules.

---

## 2. Hardware Environment

- **Modules:** Seeed LoRa-E5 Mini (STM32WLE5)
- **Firmware:** Meshtastic (Serial Interface enabled)
- **Interface:** USB Serial (/dev/ttyUSB0 typically)
- **Host:** Raspberry Pi (Main/Health) and Onshore Gateway

---

## 3. Functional Requirements

The tool (`comms/lora_tester.py`) shall provide:

### 3.1 Parameter Configuration
- **Region Set:** Ability to set LoRa region (e.g., EU_868).
- **Modem Presets:** Switch between Meshtastic presets:
    - `SHORT_FAST`
    - `LONG_SLOW`
    - `VERY_LONG_SLOW`
- **Channel Config:** Set frequency and bandwidth if not using presets.

### 3.2 Live Metrics
- **RSSI Monitoring:** Signal strength of received packets.
- **SNR Monitoring:** Signal-to-noise ratio.
- **Distance Estimation:** (If GPS available on modules).

### 3.3 Test Modes
- **Ping-Pong:** Send a packet and wait for acknowledgment to measure Round Trip Time (RTT).
- **Stress Test:** Send N packets at specific intervals to measure Packet Delivery Ratio (PDR).
- **Continuous Receive:** Listen and log all incoming traffic with metadata.

### 3.4 Data Logging
- Append test results to `comms/logs/lora_tests.csv`.
- Fields: `timestamp`, `preset`, `rssi`, `snr`, `pdr`, `latency`.

---

## 4. Implementation Strategy

### 4.1 Python Dependencies
- `meshtastic` (Python API)
- `pubsub` (for event handling)
- `pandas` (for log analysis - optional)

### 4.2 CLI Interface
```bash
python3 comms/lora_tester.py --mode ping --count 10 --preset LONG_SLOW
python3 comms/lora_tester.py --mode monitor
python3 comms/lora_tester.py --set-preset SHORT_FAST
```

---

## 5. Success Criteria

- [ ] Tool can successfully connect to LoRa-E5 via Meshtastic API.
- [ ] Tool can change modem presets and verify the change.
- [ ] Tool can measure RSSI and SNR for received packets.
- [ ] Ping-Pong test works between two modules at <10m range.
- [ ] Results are logged to a CSV file.

---

## 6. Jurisdiction

This tool and its logs reside within the `comms/` directory, under the jurisdiction of the **Network_Engineer**.
