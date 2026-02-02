# Porto da Baleeira: Digital Twin Specification
**Version:** 1.0  
**Location:** Sagres, Portugal (37.0118° N, 8.9244° W)  
**Purpose:** Realistic 3D visualization and physics simulation for oil spill detection training.

---

## 1. Geographical Layout & Geometry

### 1.1 Harbor Basin
*   **Orientation:** The cove opens to the **North-Northeast (NNE)**.
*   **Protection:** Sheltered from North/West winds by cliffs and breakwater. Exposed to **Southeast (SE)** fetch.
*   **Dimensions:**
    *   **Main Breakwater:** ~350 meters long, extending from the western headland (Ponta da Baleeira) towards the East/Southeast.
    *   **Harbor Entrance Width:** ~200-250 meters between the breakwater tip and the eastern shore cliffs.
    *   **Water Depth:** Shallow near docks (2-4m), deepening to ~10-15m at the entrance.

### 1.2 Shoreline Features
*   **West Side (Ponta da Baleeira):** High vertical cliffs (~30-40m).
    *   *Visuals:* Rugged **Jurassic Limestone** (Light Gray/White) with Karst features (caves, pockets).
    *   *Vegetation:* Sparse, low-lying scrub on cliff tops (brown/green mix).
*   **South Side (Praia da Baleeira):** Small sandy beach nestled behind the breakwater root.
    *   *Visuals:* Golden sand, calm shallow water.
*   **East Side:** Lower jagged cliffs and rocky outcrops.

### 1.3 Man-Made Structures
*   **Breakwater Construction:**
    *   *Core:* Rock mound.
    *   *Armour Layer:* **Tetrapods** (large concrete 4-legged structures) randomly interlocking on the seaward side.
    *   *Capping:* Concrete walkway/road on top.
*   **Docks/Piers:** Floating pontoons inside the breakwater for fishing boats and local tour operators.
*   **Lighthouse:** Small beacon on the breakwater tip (Red/White sector light).

---

## 2. Hydrodynamic Simulation Model

### 2.1 Surface Currents
*   **Primary Driver:** Wind-induced drift (tides are secondary in this micro-basin).
*   **The "3% Rule" (Oil Drift Physics):**
    *   `Drift_Velocity = Wind_Speed * 0.03`
    *   *Example:* 20 knot wind = 0.6 knot slick speed.
    *   *Direction:* Moves **with the wind**.
*   **Wave Action:**
    *   **N Winds (Prevailing):** Calm water inside the harbor (wind shadow). Ripples moving outward.
    *   **SE Winds (Levante):** Choppy, hazardous waves entering the harbor. Oil gets pushed against the beach/docks.

### 2.2 Oil Spill Behavior
*   **Spreading:** Gravity-Inertial initially, then Viscous-Surface Tension.
*   **Visual Look:**
    *   *Fresh Oil:* Black/Brown, high opacity, high gloss.
    *   *Sheen:* Rainbow/Silver metallic reflection (thickness < 0.01mm).
    *   *Emulsified (Old):* "Chocolate Mousse" texture, matte orange/brown.

---

## 3. Atmospheric Environment

### 3.1 Wind Profiles (Critical for Scenario Generation)
*   **Scenario A: The Nortada (Standard)**
    *   *Direction:* From **North (N)**.
    *   *Effect:* Blows **over** the cliffs. Turbulence near cliff base. Pushes surface water **out** to sea (SE).
*   **Scenario B: The Levante (Storm/Hazard)**
    *   *Direction:* From **Southeast (SE)**.
    *   *Effect:* Pushes water/oil **into** the port. High wave agitation.

### 3.2 Lighting & Sky (Sagres Specific)
*   **Sun Path:**
    *   *Summer Solstice:* Peak Altitude ~76° (High, harsh shadows).
    *   *Winter Solstice:* Peak Altitude ~30° (Long shadows, golden light).
*   **Golden Hour:** Prominent due to West-facing coast nearby, but Baleeira faces East, so **Sunrise** is the dramatic lighting event here.
*   **Water Color:**
    *   *Deep Water:* Atlantic Deep Blue.
    *   *Shallows:* Turquoise/Green (sandy bottom).
    *   *Turbidity:* Low (very clear water), unless storming.

---

## 4. Visual Assets & Textures

| Asset | Material/Texture Reference | Notes |
| :--- | :--- | :--- |
| **Cliffs** | `Jurassic Limestone`, `Karst Erosion` | White/Light Grey, porous, sharp edges. |
| **Breakwater** | `Concrete Weathered`, `Tetrapods` | Grey concrete, stained by salt/algae at waterline. |
| **Water** | `Ocean Shader` | High specularity. Wave height depends on wind. |
| **Buoy** | `Safety Yellow` | Painted metal. Scratches/rust near waterline. |
| **Oil Slick** | `Iridescent Shader` | Thin film interference for sheen. Dark viscous fluid for center. |
| **Sky** | `HDRI: Coastal Portugal` | Intense blue sky, few clouds (typically). |

---

## 5. Simulation Logic for "The Other AI"

To recreate a realistic scenario, follow this logic loop:

1.  **Set Date/Time:** Determines Sun Position (Azimuth/Elevation).
2.  **Set Wind Vector:** (e.g., 15kts @ 340° N).
3.  **Spawn Buoy:** At mooring location. Calculate "Weathervane" rotation (buoy nose points to 340°).
4.  **Spawn Leak:** (e.g., at Fuel Dock coordinates).
5.  **Update Oil Particles:**
    *   Apply Gravity Spread.
    *   Apply Wind Drift (Vector = Wind_Vector * 0.03).
    *   Check Collisions (Breakwater, Beach, Buoy).
6.  **Render Camera View:** From Buoy perspective. Check if oil particles are in Frustum.
