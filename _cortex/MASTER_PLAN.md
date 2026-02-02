# OceanPulse: Master Plan

**Phase:** 1 (Prototype Validation)
**Status:** Active Development
**Task Tracking:** See `_cortex/tasks.json` for detailed task list

## Current Objectives
1. **Hardware:** Validate TDS Sensor and Relay control via Arduino Mega. (Status: SUCCESS)
2. **Connectivity:** Establish reliable Serial bridge between Mega and Pi. (Status: SUCCESS)
3. **Integration:** Connect Pis to Megas and LoRa modules according to SPEC-002. (Status: ACTIVE)
4. **Observational Center:** Build a Web Dashboard to monitor/control the unit. (Status: ACTIVE - See SPEC-001 & SPEC-002)
5. **ADT Dashboard:** Enhance oversight panel with task board, hierarchy, and delegation views. (Status: ACTIVE - See SPEC-003)

## Active Specifications
| Spec | Name | Status |
|------|------|--------|
| **SPEC-000** | **Target Architecture (North Star)** | **APPROVED** |
| SPEC-001 | Observational Center Dashboard | Active |
| SPEC-002 | Component Integration & Serial Protocol | Active |
| **SPEC-003** | **ADT Operational Dashboard (v2.0)** | **APPROVED** |

> **SPEC-000 APPROVED (2026-01-31):** The North Star is now defined. All implementation
> decisions should reference SPEC-000 for architectural alignment.

## Role Assignments
*   **Systems_Architect:** Specs, coordination, ADT compliance, MASTER_PLAN updates.
*   **Embedded_Engineer:** Implement SPEC-002 on Arduino Megas (TDS/Relay Logic).
*   **Network_Engineer:** Implement SPEC-002 Serial/LoRa Bridge on Pis.
*   **Backend_Engineer:** Update `obs_center/app.py` for dual-circuit control.
*   **Frontend_Engineer:** Implement the Main/Health control UI + ADT panel views.
*   **Overseer:** ADS compilation, panel sync to oceanpulse.pt.

