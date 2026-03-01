# OceanPulse Hardware Audit

**Version:** 0.1
**Last Updated:** 2026-02-05
**Lead Auditor:** Integration_Engineer

---

## 1. Procurement Wave 1 (Dev Sensor Platform)

| Component | Interface | Risk Factor | Integration Notes |
|-----------|-----------|-------------|-------------------|
| Dallas DS18B20 | OneWire | **Medium (Corrosion)** | The TO-92 package is NOT water-safe. Must be used in a stainless steel probe housing for dev testing. Ensure epoxy-filled probe is used. |
| Cheap pH Module | Analog | **High (Drift/Biofouling)** | Dev only. Expect significant drift and biofouling. Not suitable for deployment >24h without enclosure protection. |
| TDS Sensor (Dev) | Analog | **Medium (Calib)** | Requires baseline calibration with known solutions for meaningful data. |

---

## 2. Procurement Wave 2 (Detection & Redundancy)

| Component | Risk Factor | Mitigation Strategy |
|-----------|-------------|---------------------|
| HC-SR501 PIR | **High (Humidity)** | Passive Infrared sensors are extremely sensitive to humidity. MUST be mounted inside the top watertight case with desiccant. |
| JSN-SR04T Ultrasonic | **Low (Waterproof)** | Transducer is IP67 rated. Control board is NOT. Mount control board in hull, transducer externally. |
| Green Cell Inverter | **High (Thermal/EMC)** | Modified sine wave produces high EMI. Isolate from LoRa antennas. Ensure thermal venting inside hull. |
| Weipu Connectors | **Low** | SP21/SP13 series are excellent for IP68. Standardize pinouts immediately to avoid cross-wiring. |

---

## 3. Environmental Standards (Proposed)

| Category | Standard | Notes |
|----------|----------|-------|
| **Enclosure** | IP68 | Required for all hull penetrations. |
| **Material** | SS316 / POM-C | SS304 will tea-stain in Sagres salinity. Prefer SS316 for all external hardware. |
| **Wiring** | Tinned Copper | Standard copper will wick salt air and corrode internally. |
| **Connectors** | Weipu SP series | Standardized on SP21 (Power/UV) and SP13 (Sensors). |

---

## 4. Pending Audits (Datasheet Required)

- [ ] **Everbeam 50W UV:** Confirm 230V AC current draw for inverter sizing.
- [ ] **IMX378 Camera:** Verify thermal limits for summer port operation.
- [ ] **NE555 Circuit:** Audit relay spark suppression (flyback diode) for 30A DC load.
