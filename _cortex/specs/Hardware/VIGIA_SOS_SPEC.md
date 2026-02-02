# Vigia SOS (Project OceanPulse Phase 2)
**Technical Specification & Operational Concept**
*Last Updated: Jan 2026*

## 1. Core Mission: "Spot Guard Sentinel"
To provide continuous, automated monitoring of specific high-risk maritime zones (e.g., cliff bases, cave mouths, rip current channels).

**Operational Reality:**
*   **Effective Range:** ~50m Radius (Visual/Thermal).
*   **Role:** "Sentry Gun" logic. Placed directly in front of a hazard zone.
*   **Limitation:** "Trough Blindness." In high seas (>2.5m waves), the buoy's line of sight is periodically blocked by wave crests, reducing reliability to <30%. Optimal for coves, harbors, and calm-to-moderate swell.

---

## 2. Operational Logic: "Event-Driven Verification"

### The "Split-Link" Architecture
To conserve power and data costs, the system uses two separate communication channels.
1.  **The Pager (LoRa 868MHz):** Always ON. Handles heartbeats, sensor telemetry, and "Panic Button" signals. Low Bandwidth.
2.  **The Pipe (4G/LTE):** Normally OFF (Sleep). Wakes up *only* to stream WebRTC Video/Audio when a verified alert occurs.

### Detection Strategy
**A. Night Mode (Zero Tolerance)**
*   **Sensor:** Thermal (Lepton 3.5).
*   **Logic:** The ocean is cold/uniform. Any heat signature >30°C in the water is treated as a Tier 1 Alert.
*   **Verification:** Thermal triggers a **High-Intensity White Flash**. Optical camera takes a burst of color photos for AI confirmation.

**B. Day Mode (Smart Filtering)**
*   **Sensor:** Optical 180° Fisheye.
*   **Geofencing:** Defines a virtual "Kill Zone" (e.g., 5m from jagged rocks).
    *   **Boats/SUPs:** Ignored if safely offshore OR moving fast (>5 knots).
    *   **Alert:** Triggered if an object enters the "Kill Zone" OR is drifting randomly/slowly (body speed).

---

## 3. Hardware Architecture (Phase 2 Add-ons)

### A. "The Watchman" (Vision Stack)
*   **Thermal Camera:** **FLIR Lepton 3.5** (Radiometric). Detects "Hot Blobs" (heads) in cold water.
*   **Visual Camera:** **Arducam 180° Fisheye** (IMX291 Low Light).
*   **Illumination:** **White LED Strobe** (Replacing UV). Essential for color verification of objects at night.

### B. "The Brain & Comms"
*   **AI Accelerator:** **Raspberry Pi AI Kit (Hailo-8L)**. 13 TOPS for real-time object classification and vector tracking.
*   **Broadband Bridge:** **4G/LTE Modem (e.g., SIM7600G-H)**. The high-speed pipe for live video intervention.
*   **"The Voice" (Interactive Audio):**
    *   **Speaker:** **Marine PA Horn (e.g., Standard Horizon 240SW)**. 15W, IP67. Allows the operator to shout warnings or comfort victims.
    *   **Amp:** **Class D Amplifier (PAM8610)**. 10W efficient audio driver.

### C. "The Lifeline" (Connectivity)
*   **LoRa Mesh:** High-gain 868MHz Antenna (5-8dBi) for "Fisherman's Fob" reception.
*   **Fisherman's Fob:** LILYGO T-Beam (LoRa + GPS). A wearable "Panic Button" for local fishermen.

---

## 4. Operational Logic: "Event-Driven Verification"

### The "Split-Link" Architecture
To conserve power and data costs, the system uses two separate communication channels.
1.  **The Pager (LoRa 868MHz):** Always ON. Handles heartbeats, sensor telemetry, and "Panic Button" signals. Low Bandwidth.
2.  **The Pipe (4G/LTE):** Normally OFF (Sleep). Wakes up *only* to stream WebRTC Video/Audio when a verified alert occurs.

### Detection Strategy
**A. Night Mode (Zero Tolerance)**
*   **Sensor:** Thermal (Lepton 3.5).
*   **Logic:** The ocean is cold/uniform. Any heat signature >30°C in the water is treated as a Tier 1 Alert.
*   **Verification:** Thermal triggers a **High-Intensity White Flash**. Optical camera takes a burst of color photos for AI confirmation.

**B. Day Mode (Smart Filtering)**
*   **Sensor:** Optical 180° Fisheye.
*   **Geofencing:** Defines a virtual "Kill Zone" (e.g., 5m from jagged rocks).
    *   **Boats/SUPs:** Ignored if safely offshore OR moving fast (>5 knots).
    *   **Alert:** Triggered if an object enters the "Kill Zone" OR is drifting randomly/slowly (body speed).

### C. Intervention (The "Voice of God")
*   Once a human is confirmed, the operator activates the **Marine Horn**.
*   **Psychological Aid:** "Stay calm, help is coming. Do not swim against the current."
*   **Crowd Control:** "You are in a restricted dangerous zone. Exit immediately."

---

## 5. Economic & Strategic Value
*   **Cost Equivalence:** The hardware cost (~€830 upgrade) is fraction of a single SAR helicopter deployment.
*   **Psychological Impact:** Being able to speak to a drowning person ("We see you") reduces panic-induced drowning significantly while assets are en route.
*   **Efficiency:** Acts as a "force multiplier," allowing one officer to monitor 10 high-risk coves simultaneously.
