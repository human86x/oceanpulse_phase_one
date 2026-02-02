# SPEC-002: Component Integration & Serial Protocol

## 1. Physical Topology
- **System A (Main):** Pi 5 <-> Arduino Mega (Serial over USB: `/dev/ttyACM0`)
- **System B (Health):** Pi 3 <-> Arduino Mega (Serial over USB: `/dev/ttyACM0`)
- **Relay Control:** Both Megas use **Pin 2** for Relay signal (Active HIGH).
- **TDS Sensor:** Mega A (Main) uses **Pin A0** (Analog Input).

## 2. Serial Protocol (Pi <-> Mega)
Communications must use a JSON-framed string protocol over 115200 baud.

### 2.1 Pi to Mega Commands
- `{"cmd": "RELAY", "val": 1}` -> Energize Relay.
- `{"cmd": "RELAY", "val": 0}` -> De-energize Relay.
- `{"cmd": "GET_TDS"}` -> Request TDS reading (System A only).

### 2.2 Mega to Pi Responses
- `{"status": "OK", "relay": 1}` -> Confirm relay state.
- `{"status": "DATA", "tds": 450, "unit": "ppm"}` -> TDS telemetry.
- `{"status": "ERROR", "msg": "reason"}` -> Error reporting.

## 3. Control Panel Integration
The `obs_center` dashboard must:
1. Fetch data from both System A and System B via the Python Bridge.
2. Provide two distinct control cards: **Main Circuit** and **Health Circuit**.
3. Display a "System Status" summary (Aggregated Heartbeat).
