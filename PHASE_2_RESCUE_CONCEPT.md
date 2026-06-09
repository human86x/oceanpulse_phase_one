# OceanPulse Phase 2: "Guardian" (Search & Rescue Support)

**Target Audience:** Bombeiros Voluntários de Vila do Bispo / Autoridade Marítima Nacional (ISN).
**Problem:** High cost and complexity of locating lost individuals (fishermen, hikers) or predicting drift patterns for "Man Overboard" scenarios in the rugged Sagres/Algarve waters.

## 1. The Financial Argument (The "Why")
*   **Helicopter Costs:** Operating an AW139/Merlin search helicopter costs **€3,000 - €5,000+ per hour**.
*   **Search Window:** Reducing search time by just 60 minutes saves enough money to fund the entire OceanPulse hardware network for a year.
*   **Risk:** Rescuers often put themselves in danger searching near cliffs in bad weather. Remote sensing reduces this risk.

## 2. Technical Capabilities (The "How")

### A. Real-Time Drift Prediction ("Where did they go?")
*   **Current State:** Search grids are often based on general models.
*   **OceanPulse Value:** Our buoys provide *live*, hyper-local current and wind data.
*   **Feature:** "Drift Vector API." A simple tool where a rescue coordinator clicks "Last Known Location" on our map, and we calculate a probability cone based on the *actual* water movement measured by our sensors in the last hour.

### B. "Cliff Sentry" (Fall Detection)
*   **Technology:** Thermal/Optical cameras on coastal buoys or cliff-top nodes.
*   **Application:** Detecting heat signatures or movement in restricted zones (e.g., base of cliffs) at night or during storms.
*   **Alert:** Instant notification to the station if a thermal anomaly (human size) is detected in a "No Go" zone.

### C. The "Fisherman's Fob" (LoRa Beacon)
*   **Concept:** A low-cost (<€15) waterproof LoRa button given to local pescadores (percebes pickers).
*   **Function:**
    *   **Panic Button:** Press to send instant GPS coordinates to the OceanPulse Mesh.
    *   **"Dead Man" Switch:** (Advanced) Accelerometer detects a high-impact fall or sudden lack of movement.
*   **Network:** Uses the same LoRa Mesh we are building for the buoys. No cellular signal needed (crucial for blind spots under cliffs).

### D. "Scream Sentry" (AI Voice Distress Detection)
*   **Origin:** Paul's Concept (Jan 9).
*   **Tech:** Waterproof MEMS microphones + Edge AI (TinyML) running on the Buoy's Pi 5.
*   **Function:** Continuous listening for specific audio patterns:
    *   **Trigger:** Human distress frequencies (screams, "Help!") vs. background ocean noise.
    *   **Filter:** AI model trained to ignore seagulls, wind, and crashing waves.
*   **Value:** Automatic alert for victims who fall in without a Fob or Phone.

## 3. Implementation Strategy

### Step 1: Data Integration (Low Friction)
*   Provide Bombeiros with a specialized "Command Dashboard" (Tablet/Web) that shows live sea state (Wave Height, Current Direction).
*   **Goal:** Help them decide *which* boat to launch or if it's safe to rappel.

### Step 2: Pilot Program (The "Black Box")
*   Deploy 1-2 "Dummy Beacons" during a training exercise.
*   Challenge: "Find the beacon using OceanPulse triangulation vs. Visual Search."
*   **Metric:** Compare time-to-find.

## 4. Funding Potential
*   **Civil Protection Grants:** EU funding for "Disaster Resilience."
*   **Local Municipality (Câmara Municipal):** Direct budget for public safety tools.
