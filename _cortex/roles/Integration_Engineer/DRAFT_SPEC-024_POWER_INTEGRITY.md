# SPEC-024: Power & Reset Integrity

**Status:** DRAFT
**Priority:** CRITICAL
**Owner:** Integration_Engineer
**References:** SPEC-012 (Integration), REQ-021 (Main Unresponsive)

---

## 1. Problem Statement

Two critical hardware risks have been identified that likely contribute to the "Main Arduino Unresponsive" state:
1.  **Back-Powering via USB:** The Arduino Megas are powered by 12V ATX/Battery but also connected to the Pi via USB. Potential for 5V back-feeding into the Pi's rail, causing USB controller lockups.
2.  **Relay EMI/Inductive Spikes:** The 30A relay controlling the Inverter/UV Strobe lacks spark suppression. High-current inductive loads generate spikes that can latch up or damage the MCU's USART (Serial) hardware.

---

## 2. Proposed Mitigations

### 2.1 Galvanic Isolation (USB)
The USB connection between Pi and Arduino SHOULD use a **USB Isolator** (ADuM3160 based) to prevent ground loops and back-powering. 
- *Alternative:* Sever the 5V trace inside the USB cable, allowing only D+/D-/GND to connect (since Arduino has independent 12V power).

### 2.2 Spark Suppression (Relays)
ALL relays (Watchdog and UV Strobe) MUST have flyback protection:
- **DC Loads (Relay Coil):** 1N4007 Diode across the coil.
- **High-Current DC Switching (30A Relay):** 1N5408 or larger flyback diode across the load IF switching DC.
- **Inverter Switching (AC Side):** RC Snubber circuit across the relay contacts to prevent arcing.

### 2.3 Hardened Serial Protocol
To verify the "Reset" state, the firmware MUST report its reset reason:
- **MCUSR Register:** Report `EXTRF` (External Reset), `WDRF` (Watchdog Reset), or `PORF` (Power-on Reset) in the `READY` message.
- **Heartbeat:** Implement a blinking LED (Pin 13) that is controlled EXCLUSIVELY by the main loop to provide visual "Ground Truth" of MCU health.

### 2.4 Hardware Watchdog
Firmware MUST use the internal AVR Hardware Watchdog Timer (WDT) with a 8s timeout. 
- The software-only watchdog currently implemented in `loop()` is insufficient to recover from MCU hangs.
- `wdt_reset()` MUST be called in `loop()`.

---

## 3. Physical Audit Checklist

1.  **Flyback Diodes:** Confirm presence on all relays.
2.  **Common Ground:** Verify single-point grounding to avoid loops.
3.  **USB 5V:** Measure voltage on Pi USB ports when 12V ATX is on but Pi is off. If >0.5V, back-powering is confirmed.

---

## 4. Verification

- [ ] Success: System A Pi 5 can be power-cycled via System B Relay and boot to 0 uptime.
- [ ] Success: Serial communication remains stable during UV Strobe firing (high EMI event).
