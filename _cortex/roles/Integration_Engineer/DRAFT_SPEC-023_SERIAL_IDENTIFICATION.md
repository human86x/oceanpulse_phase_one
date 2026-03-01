# SPEC-023: Serial Path & Device Identification

**Status:** DRAFT
**Priority:** HIGH
**Owner:** Integration_Engineer
**References:** SPEC-002 (Integration), REQ-021 (Main Unresponsive)

---

## 1. Problem Statement

Current deployment scripts and bridge software use hardcoded Linux device paths (e.g., `/dev/ttyACM0`, `/dev/ttyUSB0`). These paths are non-deterministic and change upon:
1.  USB Re-enumeration (observed on Health Pi).
2.  Device power cycles.
3.  Connecting additional hardware.

This leads to the "Wrong Device" bug where the LoRa handler attempts to talk to the Arduino or vice versa, resulting in "Unresponsive" states and command failures.

---

## 2. Proposed Solution: Persistent Naming

### 2.1 Use of `/dev/serial/by-id/`
All software components MUST transition from `/dev/ttyX` to `/dev/serial/by-id/` paths. These paths are derived from the hardware's unique serial number and vendor/product IDs.

**Example Mapping:**
- **Arduino Mega:** `/dev/serial/by-id/usb-Arduino__www.arduino.cc__0042_55838333932351E041C1-if00`
- **LoRa-E5 (CH340):** `/dev/serial/by-id/usb-1a86_USB_Serial-if00-port0`

### 2.2 Udev Rules (The "Friendly Name" Layer)
To ensure human-readability and script portability, `udev` rules shall be deployed to each Pi to create symlinks:

| Physical Device | Symlink | Target |
|-----------------|---------|--------|
| Mission Arduino | `/dev/op-mega` | Atmega2560 |
| Mission LoRa | `/dev/op-lora` | LoRa-E5 |

**Rule Definition (`/etc/udev/rules.d/99-oceanpulse.rules`):**
```bash
# Arduino Mega
SUBSYSTEM=="tty", ATTRS{idVendor}=="2341", ATTRS{idProduct}=="0042", SYMLINK+="op-mega"
# LoRa-E5 (Generic CH340 example)
SUBSYSTEM=="tty", ATTRS{idVendor}=="1a86", ATTRS{idProduct}=="7523", SYMLINK+="op-lora"
```

---

## 3. Implementation Plan

1.  **Audit:** Run `ls -l /dev/serial/by-id/` on Main and Health Pis to capture actual IDs.
2.  **Deploy Rules:** Update `ops/deploy_mission.sh` to include a setup step that installs udev rules.
3.  **Update Codebase:**
    - `bridge/main_bridge.py` default port -> `/dev/op-mega`
    - `bridge/health_bridge.py` default port -> `/dev/op-mega`
    - `bridge/lora_handler.py` default port -> `/dev/op-lora`
    - `ops/deploy_mission.sh` variables -> use friendly names.

---

## 4. Verification

- [ ] Success: Bridge connects to `/dev/op-mega` even after unplugging/replugging.
- [ ] Success: No cross-talk between LoRa and Arduino.
