# SPEC-008: LoRa Communication Chain

**Status:** APPROVED
**Priority:** HIGH
**Owner:** Network_Engineer
**Created:** 2026-02-06
**References:** SPEC-000, SPEC-002, SPEC-007

---

## 1. Purpose

Define the end-to-end communication protocol and infrastructure for relaying buoy sensor data to the Onshore Observational Center via LoRa P2P.

---

## 2. Architecture

```
[Sensors] -> [Arduino Mega] -> [Main Pi] -> [LoRa-E5 (AT)] -> [LoRa-E5 (AT)] -> [Onshore Gateway] -> [Web API]
```

---

## 3. Link Configuration

- **Frequency:** 868 MHz
- **Spreading Factor:** SF12 (Maximum range/reliability)
- **Bandwidth:** 125 kHz
- **TX Power:** 14 dBm
- **Baud Rate:** 9600 (Factory AT Firmware)
- **Protocol:** LoRa P2P (Test Mode)

---

## 4. Packet Format

### 4.1 Upstream (Buoy -> Gateway)
Format: `<CIRCUIT_ID>:<KEY>=<VALUE>`

| Circuit | Prefix | Example |
|---------|--------|---------|
| Main | M: | `M:TDS=515.2` |
| Health | H: | `H:ALIVE` |

### 4.2 Downstream (Gateway -> Buoy)
Format: `C:<TARGET_ID>:<CMD>[:<PARAM>]`

| Target ID | Command | Description |
|-----------|---------|-------------|
| `M` | `REBOOT` | Command Main Circuit to restart Health Circuit |
| `H` | `REBOOT` | Command Health Circuit to restart Main Circuit |
| `M` | `RELAY` | Toggle Main Circuit UV relay (Param: ON/OFF) |
| `B` | `PING` | Broadcast Ping (both circuits respond) |

**Example:** `C:M:RELAY:ON` -> Commands Main Circuit to turn on UV relay.
**Example:** `C:H:REBOOT` -> Instructs Health Circuit to trigger the power relay for the Main Circuit.

---

## 5. Telemetry Policy (Production)

To ensure operational integrity and simulate real-world marine conditions:
- **ALL** mission telemetry (sensor data, circuit health, GPS) MUST be transmitted via the LoRa link.
- **ALL** mission commands MUST be received via the LoRa link.
- WiFi/SSH/LAN paths are strictly for **development, maintenance, and ADS logging**. They are NOT to be used for the mission-critical telemetry loop.

---

## 6. Software Components

### 5.1 Buoy Side (`bridge/lora_handler.py`)
- Encapsulates AT command sequences.
- Converts text payloads to HEX for `AT+TEST=TXLRPKT`.

### 5.2 Onshore Gateway (`bridge/onshore_bridge.py`)
- Continuous listen loop (`AT+TEST=RXLRPKT`).
- Parses `+TEST: RX "HEX"` responses.
- Relays decoded JSON to `obs_center` API.

---

## 6. Redundancy

- Main circuit uses Primary LoRa module.
- Health circuit uses Backup LoRa module.
- Gateway listens for both prefixes.

---

## 7. Success Criteria

- [x] LoRa-E5 modules communicate using AT commands at 9600 baud.
- [x] P2P link verified between buoy and gateway.
- [x] Sensor data successfully reaches Web API.