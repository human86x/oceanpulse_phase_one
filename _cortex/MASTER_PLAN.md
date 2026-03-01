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
| **SPEC-004** | **Implementation Roadmap** | **DRAFT** |
| SPEC-005 | Dev Sensor Platform (M1) | Pending |
| SPEC-006 | Health Circuit & Self-Healing (M2) | Pending |
| SPEC-007 | LoRa Test & Configuration Tool (M2.5) | Pending |
| SPEC-008 | LoRa Communication Chain (M3) | Pending |
| SPEC-009 | Safe-Pulse Oil Detection System (M4) | Pending |
| SPEC-010 | Power Autonomy (M5) | Pending |
| SPEC-011 | Ocean-Grade Sensor Upgrade (M6) | Pending |
| **SPEC-012** | **Integration & Enclosure (M7)** | **APPROVED** |
| SPEC-013 | ADT Panel UI Refinements | APPROVED |
| **SPEC-018** | **LoRa Test Panel UI** | **APPROVED** |
| **SPEC-022** | **Lab Center Connectivity** | **APPROVED** |

> **SPEC-000 APPROVED (2026-01-31):** The North Star is now defined. All implementation
> decisions should reference SPEC-000 for architectural alignment.
>
> **SPEC-004 DRAFTED (2026-02-05):** Implementation Roadmap defines 7 milestones (M1-M7)
> bridging current state to SPEC-000. Pending human approval.
>
> **HARDWARE AUDIT COMPLETED (2026-02-05):** Integration_Engineer confirmed lab inventory
> readiness. High-risk factors identified for PIR (humidity), Inverter (EMI), and pH
> sensors (drift). Mitigation strategies integrated into SPEC-012.
>
> **SPEC-012 APPROVED (2026-02-09):** Physical integration, Weipu pinout standardization,
> and galvanic isolation strategy finalized.
>
> **SPEC-018 APPROVED (2026-02-09):** LoRa Test Panel UI specification finalized for
> real-time radio link diagnostics.
>
> **NOTE (2026-02-24):** SPEC-014 (DTTP), SPEC-015 (ADT Operational Center),
> SPEC-016 (ADT Help Page), and SPEC-017 (ADT Framework Repository) have been
> migrated to the standalone ADT Framework project. Removed from this tracker.

## Role Assignments
*   **Systems_Architect:** Specs, coordination, ADT compliance, MASTER_PLAN updates.
*   **Embedded_Engineer:** Implement SPEC-002 on Arduino Megas (TDS/Relay Logic).
*   **Network_Engineer:** Implement SPEC-002 Serial/LoRa Bridge on Pis.
*   **Backend_Engineer:** Update `obs_center/app.py` for dual-circuit control.
*   **Frontend_Engineer:** Implement the Main/Health control UI + ADT panel views.
*   **Overseer:** ADS compilation, panel sync to oceanpulse.pt.

