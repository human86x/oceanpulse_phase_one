# SPEC-012: Physical Integration & Enclosure

**Status:** APPROVED
**Priority:** HIGH
**Owner:** Integration_Engineer (build), Systems_Architect (spec)
**Created:** 2026-02-05
**Updated:** 2026-02-09
**References:** SPEC-000 (Target Architecture), SPEC-005 (Dev Sensor Platform), SPEC-006 (Health Circuit), SPEC-009 (Oil Detection), SPEC-010 (Power Autonomy)
**Source Documents:** Final Drawings of customed buoy.pdf, Door Panel Technical Requirements (DEXON Marine), Mauser.pt invoices 2025EC1351975 & 2026EC1375416, HARDWARE_AUDIT.md

---

## 1. Purpose

This specification defines the physical integration of all OceanPulse electronic subsystems into the Model 2600Fx buoy frame. It covers zone layout, shelf assignments, cable routing, hull penetrations, weight distribution, thermal management, and assembly sequence -- all with millimetric precision derived from the manufacturer's technical drawings and standardized for modularity.

---

## 2. Buoy Frame & Interior Layout

### 2.1 Overall Dimensions (Model 2600Fx)
*Source: Final Drawings of customed buoy.pdf*

| Measurement | Value | Notes |
|-------------|-------|-------|
| **Float diameter** | 1200mm | Circular HDPE float body |
| **Float height** | 600mm | Vertical height of float body |
| **Tower frame height** | 782mm | Structural frame from float top |
| **Total structure height** | 1755mm | Keel bottom to top |
| **Frame weight** | 80kg | Steel frame only |

### 2.2 Tower Structure & Door
*Source: Door Panel Tech Requirements*
- **Top platform:** 461.2 x 461.2mm
- **Internal tower height:** 974mm
- **Door opening:** Trapezoidal (419.8mm bottom x 333.6mm top x 824.5mm height).
- **Material:** Q235 Steel (Final: Hot-Dip Galvanized).

### 2.3 Internal Shelf System
The tower contains **2 shelves** with **2 watertight boxes**.
- **Lower shelf:** Larger watertight box (RPi 5 + Arduino Mega Main).
- **Upper shelf:** Smaller watertight box (RPi 3 B+ + Arduino Mega Health + LoRa modules).

---

## 3. Connector Standardization (IP68)

To ensure modularity and prevent cross-wiring errors, all hull penetrations and bus connections will use **Weipu SP Series** connectors with the following pinout standards:

### 3.1 Main Power & Comms Bus (Weipu SP21 - 7 Pin)
Used for cross-zone distribution (Zone C to Zone B) and high-density signal paths.
| Pin | Function | Gauge | Notes |
|-----|----------|-------|-------|
| 1 | GND | 18AWG | Common Ground |
| 2 | +12V (Constant) | 18AWG | Main Battery Bus |
| 3 | +12V (UV Switched)| 16AWG | Inverter Power Path |
| 4 | RS485-A | 22AWG | Sensor Data Bus |
| 5 | RS485-B | 22AWG | Sensor Data Bus |
| 6 | System A Heartbeat| 24AWG | Cross-Watchdog |
| 7 | System B Heartbeat| 24AWG | Cross-Watchdog |

### 3.2 High Power / UV (Weipu SP21 - 3 Pin)
Used for 230V AC or high-current DC loads (Penetration P2).
| Pin | Function | Wire Colour |
|-----|----------|-------------|
| 1 | Live / Pos | Brown |
| 2 | Neutral / Neg | Blue |
| 3 | Earth / GND | Green/Yellow |

### 3.3 External Sensors (Weipu SP13 - 4 Pin)
Used for underwater and mast-head sensors (Penetrations P4, P6).
| Pin | Function | Notes |
|-----|----------|-------|
| 1 | VCC (+5V/3.3V) | Standardized per sensor |
| 2 | GND | |
| 3 | Data / A | I2C SDA / RS485-A / OneWire |
| 4 | Clock / B | I2C SCL / RS485-B |

---

## 4. Environmental & Galvanic Strategy

### 4.1 Material Isolation (Galvanic Protection)
The Hot-Dip Galvanized (HDG) steel frame must NOT come into direct electrical contact with dissimilar metals to prevent accelerated corrosion.
- **Isolation:** Use Nylon or POM-C shoulder washers for all mounting points (Aluminum cases, SS316 brackets).
- **Sacrificial Anodes:** Two M12 Zinc anodes must be bolted to the lower submerged frame to protect the HDG coating from electrolysis.

### 4.2 Material Standards
- **External Hardware:** SS316 only (SS304 will tea-stain).
- **Wiring:** Tinned Copper mandatory (prevents internal wicking/corrosion).
- **Cable Ties:** SS316 or UV-stabilized Nylon (SS316 preferred for external).

---

## 5. Integration Verification (Gate Tests)

Final assembly is only authorized upon successful completion of the following Gate Tests:

1. **Vacuum Test:** The empty electronics enclosure must hold a 5psi vacuum for 1 hour to verify seal integrity.
2. **Standardization Audit:** Verify that any SP13 sensor can be plugged into any SP13 port without electrical damage.
3. **Galvanic Continuity:** Use a multimeter to verify >10MΩ resistance between any electronics case and the buoy frame.
4. **Buoyancy Margin:** Verify total deployed weight (~95kg) remains within the displacement limits of the 1200mm HDPE float with a minimum 40% reserve buoyancy.

---

## 6. Zone Layout & Assembly

(Refer to Sections 3-10 of the original draft for detailed Zone mapping, Weight Budget, and Thermal Management strategy. These sections remain binding under the APPROVED status.)

---

*"Integration is where theory meets metal. Every millimetre matters."*
