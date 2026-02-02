# OceanPulse UV Safety Specification (Level 0 Hazard Control)
**Version:** 1.0
**Status:** MANDATORY
**Scope:** All 365nm UV Emitters (System A)

## 1. Hazard Analysis
The buoy utilizes a **40W 365nm UV-A Array** (Class 3B equivalent risk).
*   **Risk:** Instant photokeratitis (Welder's Flash) and retinal damage at < 5m.
*   **Environment:** Public Port (Uncontrolled civilians/traffic).
*   **Zero Harm Goal:** No human shall be exposed to the direct beam or specular reflection at < 10m.

## 2. Hardware Safety Layers (Physical)

### 2.1 The "Horizon Cut-Off" Shroud
*   **Requirement:** The LED housing must be fitted with a physical baffle (aluminum or opaque UV-stabilized plastic).
*   **Geometry:**
    *   Mounting Height: 2.0m.
    *   Tilt Angle: 45° Down.
    *   **Cut-off:** The shroud must extend continuously to block all upward light emission.
    *   **Result:** The beam is geometrically incapable of shining above the waterline-horizon angle.

### 2.2 Fail-Safe Wiring
*   **Relay Type:** The relay controlling the UV Array MUST be **Normally Open (NO)**.
*   **Behavior:** In event of power loss, System A crash, or logic freeze, the circuit opens, and lights extinguish immediately.
*   **Hardware Interlock (Optional but Recommended):** A physical switch in series with the UV power line that opens if the buoy is tilted > 60° (e.g., being hauled onto a deck).

### 2.3 Reflection Safety Analysis (Physics-Based)
*   **Concept:** Mitigation of reflected UV energy from the water surface.
*   **Fresnel Calculation:** At the engineered incidence angle of 45°, the specific reflectivity of seawater is calculated at **~2.75%**.
    *   *Input:* 40W Source.
    *   *Reflected:* < 1.1W (Diffuse).
    *   *Verdict:* Reflected energy is below the threshold for immediate ocular injury (Eye Safe).
*   **Geometric Escape:** The reflected beam exits at a steep 45° angle.
    *   At 5m distance, the beam center is >5m altitude.
    *   This trajectory ensures the beam clears the "Head Height" of personnel in nearby vessels naturally.

## 3. Active Safety Layers (The "Triple Lock")

### 3.1 PIR Proximity Curtain (Life Detection)
*   **Sensors:** 3x HC-SR501 (or waterproof equivalent) PIR Motion Sensors.
*   **Mounting:** Arranged 120° apart on the mast, facing outward/downward.
*   **Logic:** `IF PIR_Signal == HIGH`: **HARD ABORT**.

### 3.2 Ultrasonic "Head" Check (Object Detection)
*   **Sensor:** JSN-SR04T Waterproof Ultrasonic Rangefinder.
*   **Mounting:** Pointing directly down at the water target (Parallel to light beam).
*   **Logic:**
    *   Normal Water Distance: ~2.0m.
    *   **Veto Threshold:** If `Distance < 1.5m` -> **HARD ABORT**.
    *   *Reason:* Indicates a boat hull or person is physically blocking the beam path.

### 3.3 Visual Pre-Scan (Light Detection)
*   **Sensor:** Main Camera (High Gain Mode).
*   **Logic:** If `Max_Pixel_Brightness > Threshold` (indicating Nav lights or Flashlights) -> **HARD ABORT**.

### 3.4 Visual Warning Beacon
*   **Hardware:** 1x High-Intensity Amber LED Strobe (Visible Light).
*   **Sequence:**
    1.  **T-2s:** Amber Strobe ON (Flash 4Hz).
    2.  **T-0s:** Amber OFF.
    3.  **Action:** UV Pulse (Max 200ms).

### 3.4 Hardware Pulse Limiter (The "Anti-Bug")
*   **Mechanism:** A NE555 Timer (Monostable Mode) or RC circuit placed between the GPIO trigger and the MOSFET Gate.
*   **Function:** Limits the maximum possible "ON" time to **500ms**, regardless of the input signal.
*   **Scenario:** If the Python script crashes while holding the GPIO pin HIGH, the 555 timer will still cut the circuit after 0.5s, preventing continuous exposure.

## 4. Operational Logic (Software)

### 4.1 The "Pulse-and-Sense" Protocol
The previous "Always On" or "1 second wait" logic is **BANNED**.

**New Sequence:**
1.  **Safety Check:** Check PIR Sensors. If clear -> Proceed.
2.  **Visual Scan:** Camera takes passive high-gain ISO image.
    *   *Algorithm:* Detect "Bright Blobs" (Navigation lights, flashlights).
    *   *Logic:* If Max_Luminance > Threshold -> **ABORT** (Assume vessel nearby).
3.  **Warning:** Activate Amber Strobe for 2.0 seconds.
4.  **Fire:**
    *   Open Shutter (Long Exposure).
    *   **Trigger UV Flash (Duration: < 200ms).**
    *   Close Shutter.
5.  **Cool Down:** Enforce 10-second lockout.

## 5. Maintenance Mode
*   **Physical Switch:** A magnetic reed switch or physical toggle on the buoy exterior must completely disconnect the UV circuit for safe handling by maintenance crews.
