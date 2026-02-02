# Project Specification: OceanPulse Phase 1 - Port Sentry Buoy
**Version:** 1.0  
**Target Environment:** Fishing Port / Coastal Harbor  
**Primary Objective:** Autonomous detection of hydrocarbon spills (Diesel/Oil) and environmental monitoring.  
**Constraint Level:** Low Budget, Single-Point Mooring (Rotating Buoy), Low Bandwidth (Wi-Fi/LoRa), Solar Power.

---

## 1. Core System Concept
**The "Hybrid Spectral Sentry"**
Instead of using expensive industrial sensors ($6k+), this system utilizes **Edge-based Computer Vision** augmented by optical physics to detect oil spills. The system operates in two distinct modes to solve the challenge of day/night detection and sun glare.

* **Day Mode:** Passive optical analysis using **Polarization** to detect surface texture anomalies (smoothing) and color anomalies (rainbow sheens).
* **Night Mode:** Active **UV Fluorescence** (365nm) to detect glowing hydrocarbons against dark water.

---

## 2. Hardware Architecture (Bill of Materials)
**Detailed Schematic:** [OIL_DETECTION_SCHEMATIC.md](./OIL_DETECTION_SCHEMATIC.md)

### A. The Controller (Edge Compute)
* **Unit:** Raspberry Pi 4 Model B (4GB RAM) or NVIDIA Jetson Nano.
* **OS:** Raspberry Pi OS Lite (Headless).
* **Role:** Sensor orchestration, image processing (OpenCV), decision logic, data transmission.

### B. The Vision Stack (The "Eye")
* **Camera Sensor:** **Raspberry Pi Camera Module 3 (Wide)**.
    * *Why:* Built-in HDR (High Dynamic Range) is critical for handling water reflections. 120° Wide FOV provides large surface area coverage (~130m²).
* **Day Filter:** **Circular Polarizing Filter (CPL)**.
    * *Spec:* 37mm Mobile Phone CPL clip-on (disassembled) or similar.
    * *Mounting:* Fixed permanently to the lens housing at the angle of maximum glare reduction.
* **Night Illumination:** **365nm UV-A LED Emitter (Pulse Mode Only)**.
    * *Spec:* 40W (4x10W) Waterproof UV Array. **Safety Critical: Must use Normally Open (NO) Relay.**
    * *Control:* Hardware-interlocked via PIR sensors.
* **Safety Hardware:**
    *   **PIR Sensors:** 3x Motion detectors to identify nearby humans/vessels.
    *   **Warning Beacon:** Amber Visible LED Strobe.

### C. Environmental Sensors (Telemetry)
* **Rotation/Heading:** **MPU-9250** (9-Axis IMU).
    * *Role:* Provides compass heading to prevent the camera from taking photos directly into the sun (Sun Glint Rejection).
* **Water Quality:** Standard probe stack (Temperature, Dissolved Oxygen, Salinity/Conductivity).

### D. Power & Connectivity
* **Power:** 50W Solar Panel + MPPT Controller + LiFePO4 Battery.
* **Comms:** Wi-Fi (Primary for Port) / LoRaWAN (Backup for telemetry).

---

## 3. Mechanical Design & Deployment

### Mounting Geometry
* **Height:** Camera mounted **2.0 meters** above the waterline on the buoy mast.
* **Angle:** Camera tilted down at **45 degrees** relative to the horizon.
    * *Reason:* Optimizes sky reflection to highlight oil sheen contrast.
* **Orientation:** Fixed relative to the buoy chassis.

### The "Rotating Buoy" Solution
Since the buoy uses single-point mooring, it will rotate.
1.  **Compass Check:** The MPU-9250 reads the buoy's heading.
2.  **Sun Logic:** System calculates Sun Position based on UTC time.
3.  **Veto:** If `|Buoy_Heading - Sun_Azimuth| < 45 degrees`, the system aborts image capture to avoid blinding the sensor.

---

## 4. Software Logic & Algorithms (Python/OpenCV)

The system avoids heavy Deep Learning (LLMs/Transformers) in favor of lightweight Classical Computer Vision.

### State Machine Loop
1.  **Wake Up** (Every 1-5 minutes).
2.  **Check Time:** Determine Day vs. Night.
3.  **Execute Mode:**

#### Mode A: Night (Fluorescence)
* **Safety Protocol:** "Pulse-and-Sense" (See `SAFETY_SPEC.md`)
    1.  **PIR Check:** Ensure no thermal motion nearby.
    2.  **Nav Light Scan:** Check camera for visible boat lights.
    3.  **Warn:** Flash Amber Strobe (2s).
* **Action:** Trigger UV Pulse (100-200ms) synchronized with Shutter.
* **Algorithm:** `Thresholding`
    * Convert Image to Grayscale.
    * Count pixels with Luminance > 200 (Bright White/Blue).
    * **Logic:** If `Bright_Pixel_Count > Threshold`: **POSSIBLE OIL DETECTED**.

#### Mode B: Day (Texture & Sheen)
* **Action:** Check MPU-9250 Compass. If facing Sun -> Abort. Else -> Capture Image.
* **Pre-Check (Glare):** Analyze Histogram. If >30% pixels are pure white (255), discard image (Glare Blindness).
* **Algorithm 1 (Texture):** `Canny Edge Detection`
    * Calculate edge density of the water surface.
    * **Logic:** If `Edge_Density` drops significantly in a specific region (Water is unnaturally smooth): **POSSIBLE SLICK**.
* **Algorithm 2 (Color):** `HSV Color Space`
    * Isolate High Saturation / Rainbow spectrums (Diesel sheen).
    * **Logic:** If `Smooth_Area` contains `Rainbow_Sheen`: **CONFIRMED OIL**.

---

## 5. Data Transmission Strategy (Edge Processing)

**Do NOT stream video.**
* **Heartbeat:** Send text-based environmental data (Temp/Salinity/Battery) every 15 mins via MQTT/HTTP.
* **Negative Result:** If no oil is seen, send nothing (or a "Clean" status flag).
* **Positive Result:** If Logic returns "True":
    1.  Compress the captured image (JPEG, 60% quality).
    2.  Send Alert Packet: `Timestamp + GPS + Confidence_Level + Image_Thumbnail`.

---

## 6. Strategic Advantages (For Proposal)
1.  **Cost:** <$500 vs Industrial $6,000 sensors (LDI ROW).
2.  **Coverage:** Wide-angle lens monitors ~130m² vs Industrial sensors monitoring <0.5m².
3.  **Reliability:** Hybrid Day/Night approach eliminates the "Darkness" blind spot of standard cameras and the "Glassy Water" false positives of standard radar.
