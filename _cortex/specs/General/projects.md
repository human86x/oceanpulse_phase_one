# OceanPulse Project Overview

**Website:** [www.oceanpulse.pt](https://www.oceanpulse.pt)  
**Location:** Vila do Bispo, Sagres, Portugal  
**Mission:** To establish an open coastal observation network using advanced telemetry (LoRa, Edge AI) to protect the ocean, fostering a balance between science, community, and marine conservation.

## Strategic Context
*   **Global Impact:** Oceans represent a ~$24 Trillion asset and generate ~$2.5 Trillion/year in services.
*   **The Challenge:** A massive investment gap (~$175B/year) exists for SDG 14 (Life Below Water).
*   **Our Solution:** "Close the Gap Between Ocean Change and Human Response" by deploying affordable, scalable Industry 5.0 technologies.

## Project Roadmap

### Phase 1: Port Safety & Aquaculture Support (Current Focus)
**Objective:** Dual-mission deployment for hydrocarbon spill detection and water quality monitoring for local mussel farming (Finisterra Lda).
**Hardware Specification:** [Port Sentry Buoy](./oil_detection_module.md) | [Safety Spec](./SAFETY_SPEC.md)
*   **Core Tech:** "Hybrid Spectral Sentry" (Polarized Day Vision + Safe-Pulse UV Fluorescence).
*   **Safety Mandate:** "Zero Harm" architecture using Triple-Lock sensors (PIR, Ultrasonic, Vision) and Hardware Fail-safes (NE555).
*   **Platform:** Rotating buoy with dual-redundant processing (Pi 5 + Pi 3 + 2x Arduino Mega).
*   **Budget:** ~€1,650 (Tiered: €850 Basic / €1,650 Advanced).
*   **Status:**
    *   **Prototyping:** Vision pipeline with safety interlocks in development.
    *   **Hardware:** Waiting for replacement HDG frame; specialized UV/Safety BOM finalized.
    *   **Digital Twin:** Interactive BOM and Simulator live at [oceanpulse.pt/buoy/](https://oceanpulse.pt/buoy/).

### Phase 2: Beach Safety & Marine Health
**Objective:** Monitoring near-shore conditions to ensure public safety and track ecosystem vital signs.
*   **Features:** Real-time water quality, wave/current monitoring, and pollution alerts.

### Phase 3: Seafood Quality
**Objective:** Leveraging data to ensure the sustainability and safety of local seafood resources.

## Technical Resources
*   **Repository:** [marine_telemetry](https://github.com/human86x/marine_telemetry)
*   **Communication:** LoRa Mesh Networks, MQTT/HTTP over Wi-Fi.
*   **Power:** Solar + LiFePO4 for autonomous operation.
