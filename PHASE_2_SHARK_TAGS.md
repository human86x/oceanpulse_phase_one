# Phase 2 Feature: Acoustic Shark Tag Integration
**Origin:** Request from Marine Biology PhD contact.
**Status:** Concept / Feasibility Study.

## 1. The Concept
To utilize the **OceanPulse Buoy Network** as a real-time gateway for tracking tagged marine life (Sharks, Rays, Tuna).

## 2. The Problem
*   **Current Tech:** Researchers typically use "Listening Stations" (receivers) anchored to the seafloor.
*   **Data Latency:** They must dive to retrieve these stations manually every 6-12 months to get the data.
*   **Risk:** If a station is lost (trawlers, storms), the data is gone forever.

## 3. The OceanPulse Solution
*   **"Live" Listening:** Equip our Phase 2 buoys with an **Acoustic Hydrophone** (e.g., 69 kHz receiver).
*   **The Gateway:**
    1.  Shark swims past buoy (range ~500m - 1km).
    2.  Buoy "hears" the acoustic tag ID.
    3.  Buoy logs the timestamp + ID.
    4.  Buoy transmits data immediately via **LoRa Mesh** to the cloud.
*   **Result:** Researchers get *real-time* alerts of animal movements without getting wet.

## 4. Hardware Implications
*   **Sensor:** Need to source an OEM Hydrophone Module (compatible with VEMCO/Innovasea tags or similar open standards).
*   **Power:** Continuous listening consumes power. Phase 2 power budget must account for this (DSP processing).
*   **Cost:** Hydrophones are expensive. Need to explore low-cost Open Source alternatives (e.g., Open Acoustic Devices).

## 5. Strategic Value
*   **Partnerships:** Instant collaboration with Universities (CCmar, UAlg).
*   **Public Interest:** "Shark Tracker" apps are hugely popular for engagement.
