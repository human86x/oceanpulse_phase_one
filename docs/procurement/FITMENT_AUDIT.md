# OceanPulse Fitment Audit (Physical Blockers)

**Version:** 1.0
**Last Updated:** 2026-02-27
**Status:** RED (Major Blockers Identified)
**Lead Auditor:** Integration_Engineer

---

## 1. Physical Integration Blockers

The following components have been identified as having major fitment issues within the current SPEC-012 physical architecture.

| Component | Intended Location | Issue | Impact |
|-----------|-------------------|-------|--------|
| **LiFePO4 50Ah Battery** | Lower Shelf Enclosure | **Does not fit** inside the assigned watertight container. | **Critical:** Battery is currently unshielded; cannot seal hull. |
| **Solar Panel (100W)** | Buoy Tower Wall | **Too large** for mounting on a single tower wall facet. | **High:** Requires custom external frame or relocation to top platform. |

---

## 2. Technical Analysis

### 2.1 Battery Enclosure Conflict
*   **Enclosure Dimensions:** [TBD - Measure internal volume]
*   **Battery Dimensions:** [TBD - From Green Cell 50Ah datasheet]
*   **Root Cause:** Enclosure was selected for standard Lead-Acid or smaller LiFePO4; the 50Ah unit has a larger footprint than anticipated.

### 2.2 Solar Panel Dimension Conflict
*   **Tower Facet Width:** ~333.6mm (top) to ~419.8mm (bottom).
*   **Panel Width:** [TBD - Measure actual panel]
*   **Root Cause:** The panel width exceeds the trapezoidal width of the tower door/facets.

---

## 3. Proposed Mitigations

### 3.1 Battery Fix (Priority 1)
- [ ] **Option A:** Source a larger IP67 enclosure for the lower shelf.
- [ ] **Option B:** External battery box mounted to the float (requires additional hull penetration P8).
- [ ] **Option C:** Split the battery bank (2x 25Ah) if form factor allows.

### 3.2 Solar Mounting Fix (Priority 2)
- [ ] **Option A:** Horizontal mounting on the top platform (affects camera FOV/PIR range).
- [ ] **Option B:** Custom "Wing" brackets to allow panel to overhang tower facets.
- [ ] **Option C:** Source 2x 50W narrower panels to mount on opposite facets.

---

## 4. Next Steps
1. **Integration_Engineer** to measure exact delta (how many mm over limit).
2. Update **SPEC-012** once mitigation is selected.
