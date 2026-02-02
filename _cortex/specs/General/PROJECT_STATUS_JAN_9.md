# Project Status Update: Jan 9, 2026

## 1. Phase 2: "Guardian" Rescue System (Technical Definition)
**Goal:** Define specs before pitching to Bombeiros (Contact confirmed).

### A. The "Fisherman's Fob" (Panic Button)
*   **Tech:** Low-cost (<€15), waterproof LoRaWAN button.
*   **Critical Value:** Works in "Cellular Blind Spots" (e.g., base of cliffs) where phones fail.
*   **Function:** Single press sends instant GPS + ID to the OceanPulse Mesh -> Bombeiros Dashboard.

### B. Drift Vector API ("Where did they go?")
*   **Tech:** Algorithm driven by *live* Phase 1 Buoy data (Current Speed/Direction + Wind).
*   **Critical Value:** Replaces generic static models with real-time, hyper-local data.
*   **Output:** Generates a "Probability Cone" on the rescue map based on actual water movement in the last 60 mins.

### C. Cliff Sentry (Prevention)
*   **Tech:** Thermal/IR cameras on coastal nodes (or buoys facing cliffs).
*   **Critical Value:** Early warning for "No Go" zones during storms/night.
*   **Output:** Alert triggered by thermal signatures (human size) in restricted areas.

### D. Scream Sentry (AI Voice)
*   **Tech:** MEMS Microphones + Pi 5 Edge AI.
*   **Critical Value:** The "Last Resort" detection for victims with no gear.
*   **Output:** AI detects human distress screams vs. wave noise.

---

## 2. Logistics & Financials (Phase 1)

### ⚠️ Battery / Power
*   **Issue:** German (Offgridtec) order **cancelled** (delivery too long).
*   **Action:** Re-ordering immediately from **Mauser.pt** (Local).
*   **Lab Power:** Mains electricity installation confirmed for **next week**. No need to rooftop-mount the solar panels; we can build on the bench.

### ⏳ Bureaucracy
*   **EORI:** **HOLDING.** Waiting for specific advice from Chinese supplier (DexinMarine) before applying.
*   **Customs:** **CRITICAL.** Must have **~€600 cash** ready for Feb 16 (Frame arrival).

### ✅ Confirmed
*   **Lisbon Transport:** Group C Car Rental (~€210) locked in for frame pickup.
