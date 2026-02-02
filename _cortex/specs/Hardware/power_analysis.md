# OceanPulse Buoy: Power Analysis & Sizing Report
**Location:** Sagres, Portugal (Lat: 37.0° N)
**Target Autonomy:** 3 Days (No Sun)
**System Voltage:** 12V

---

## 1. Load Calculation (Power Consumption)

**Operational Profile (User Defined):**
*   **System A (Mission):** ALWAYS ON (Real-Time Data every 5-10s).
*   **System B (Health):** ALWAYS ON.
*   **Oil Detection:** Night Only (UV Active). Day Mode is passive/idle.

### Scenario C: "Real-Time Always On" (100W Optimized)
*   **System A (Pi 5):**
    *   *Daytime:* Idle/Comms Only (Low CPU). ~3.5W.
    *   *Nighttime:* Active Vision/UV (Short Bursts). ~4.0W avg.
*   **System B (Pi 3):** Idle/Monitoring. ~1.5W.
*   **Sensors & LoRa:** ~0.5W.
*   **Conversion Losses:** ~1.0W.
*   **Total Continuous Draw:** **~6.5 Watts**

**Daily Energy Demand:**
$$ 6.5W \times 24h = \mathbf{156 Wh / day} $$

---

## 2. Solar Generation (Sagres) - 100W Panel

*   **Solar Irradiance (Winter - Dec/Jan):** ~2.5 Peak Sun Hours (PSH).

### With a 100W Panel (Confirmed):
*   **Winter Generation:** $100W \times 2.5h \times 0.75 \text{ (eff)} \approx \mathbf{187 Wh / day}$

**Verdict:** 
*   **Generation (187 Wh)** > **Demand (156 Wh)**.
*   **Margin:** +31 Wh/day surplus in Winter. **VIABLE.**

---

## 3. Battery Sizing (Autonomy)

**Target:** 3 Days of Darkness.
*   **Demand:** 156 Wh/day.
*   **Total Capacity Needed:** $156Wh \times 3 \text{ days} / 0.8 \text{ (DOD)} = \mathbf{585 Wh}$.
*   **Battery Size:** 12.8V 40Ah = 512Wh.
    *   *Autonomy:* ~2.6 Days in worst-case winter storm.
    *   *Recommendation:* **40Ah is acceptable**, but 50Ah-60Ah would hit the full 3-day target comfortably.

---

## 4. Final Configuration
1.  **Panel:** **100W Rigid Marine Panel**.
2.  **Battery:** **40Ah - 60Ah LiFePO4**.
3.  **Strategy:** Both systems run 24/7. Oil detection runs strictly at night to balance the power budget.
