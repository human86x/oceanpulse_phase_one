# OceanPulse Hivemind: Roles & Jurisdictions

This document defines the professional roles, their specific focus areas, and their technical jurisdictions within the OceanPulse project.

## The Roster

*   **Systems_Architect** (The Tech Lead)
    *   *Focus:* Technical Strategy, System Design, Spec Approval, Redundancy & Safety.
    *   *Jurisdiction:* `_cortex/` root, `MASTER_PLAN.md`, `specs/`.

*   **Product_Manager** (The Visionary)
    *   *Focus:* User Requirements, Market Fit, Features, Budget, Timeline.
    *   *Jurisdiction:* `_cortex/requirements/`, `docs/business/`.

*   **Mechanical_Engineer** (The Hull)
    *   *Focus:* CAD, 3D Printing, Waterproofing, Mounting, Thermal.
    *   *Jurisdiction:* `_cortex/roles/Mechanical_Engineer/`, `hardware/mechanical/`.

*   **Electrical_Engineer** (The Spark)
    *   *Focus:* PCB Design, Power Budget, Wiring Diagrams.
    *   *Jurisdiction:* `_cortex/roles/Electrical_Engineer/`, `hardware/electrical/`.

*   **Embedded_Engineer** (The Core)
    *   *Focus:* Arduino/C++, RTOS, Sensor Drivers, Watchdogs.
    *   *Jurisdiction:* `_cortex/roles/Embedded_Engineer/`, `firmware/`.

*   **Network_Engineer** (The Link)
    *   *Focus:* LoRa, WiFi, Serial Bridges, Protocols (MQTT/HTTP).
    *   *Jurisdiction:* `_cortex/roles/Network_Engineer/`, `comms/`, `bridge/`.

*   **Backend_Engineer** (The Base)
    *   *Focus:* Server Logic, Database, API Endpoints, Python/Flask.
    *   *Jurisdiction:* `_cortex/roles/Backend_Engineer/`, `obs_center/backend/`.

*   **Frontend_Engineer** (The View)
    *   *Focus:* Dashboard UI, Data Visualization, User Interaction.
    *   *Jurisdiction:* `_cortex/roles/Frontend_Engineer/`, `obs_center/frontend/`, `adt_panel/`.

*   **DevOps_Engineer** (The Sentry)
    *   *Focus:* Deployment, Security, Git, CI/CD, System Hardening.
    *   *Jurisdiction:* `_cortex/roles/DevOps_Engineer/`, `ops/`.

*   **QA_Engineer** (The Shield)
    *   *Focus:* Automated Testing, Integration Testing, Stress Testing.
    *   *Jurisdiction:* `tests/`.

*   **Integration_Engineer** (The Assembler)
    *   *Focus:* Technical Hardware Selection, Physical Fitment (Dimensions/Mass), Environmental/Galvanic Compatibility, Datasheet Auditing.
    *   *Jurisdiction:* `_cortex/roles/Integration_Engineer/`, `docs/procurement/`.

*   **Overseer** (The Chronicler)
    *   *Focus:* ADT Compliance, ADS Management, Reporting, Human Oversight.
    *   *Jurisdiction:* `_cortex/ads/`, `adt_panel/`, `_cortex/reports/`.
    *   *Special:* Compiles ADS and publishes to `oceanpulse.pt/adt_panel/`.

## Coordination System

Both AI agents (Claude and Gemini) use the following shared coordination system:

```
_cortex/
├── active_tasks/     # Lock files prevent conflicts
├── work_logs/        # Session logs show who did what
├── requests.md       # Inter-agent communication
└── MASTER_PLAN.md    # Shared objectives
```

### Lock Protocol
Before editing any file, agents must:
1. Check `_cortex/active_tasks/` for existing locks.
2. Create a lock file if proceeding.
3. Release lock upon completion.

### Work Logs
Each session appends to: `_cortex/work_logs/<YYYY-MM-DD>_<role>.md`.