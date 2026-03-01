# The Universal ADT Framework (v2.0)
## Governance-Native Multi-Agent Orchestration

### 1. The Prime Directive
"Governance is an intrinsic system property, not an external overlay." 
Every action taken by an AI agent must be authorized by intent, documented in a ledger, and cryptographically verified.

---

### 2. The Four Pillars of the System

#### I. The Authoritative Data Source (ADS) - "The Ledger"
*   **Location:** `_cortex/ads/events.jsonl`
*   **Rule:** Every single action (file edits, shell commands, decisions) MUST be logged.
*   **Principle:** If it is not in the Ledger, it did not happen. The Ledger is the single source of truth for all dashboards and human oversight.

#### II. The Integrity Chain - "The Cryptographic Seal"
*   **Mechanism:** Every new log entry contains a **SHA-256 Hash** of the previous entry.
*   **Result:** This creates an immutable "Hash Chain." If any part of the project history is altered or deleted, the chain breaks, and the system alerts the Human.
*   **Benefit:** Absolute trust in the audit trail.

#### III. Specification-Driven Development (SDD) - "Intent before Action"
*   **Rule:** "No Spec, No Code."
*   **Protocol:** Before performing technical work, an agent must draft or reference a **Specification (SPEC-XXX)**.
*   **Accountability:** Every action in the Ledger must reference an approved Spec (`spec_ref`), linking the *Work* back to the *Human's Intent*.

#### IV. Role-Based Jurisdictions - "The Guardrails"
*   **Structure:** Work is divided into specialized **Roles** (e.g., Architect, Base, Lead).
*   **Jurisdiction:** Each role has a specific "Allowed Edit Zone" (folders/files).
*   **Enforcement:** Agents are forbidden from acting outside their assigned jurisdiction without explicit human escalation.

---

### 3. The Narrative Workflow (Causal Chains)
Work is not a flat list of logs; it is a **Story**. Events are grouped into **Sessions** to visualize:
1.  **INTENT:** What the agent started out to do.
2.  **MODIFICATION:** What was actually changed.
3.  **OBSTACLE:** Real-time struggles (errors, failures, blocks).
4.  **RESOLUTION:** How the obstacle was overcome.
5.  **CONCLUSION:** The final result of the effort.

---

### 4. Implementation Logic (The "Brain" Folder)
Every project must contain a `_cortex/` directory with this structure:
*   `_cortex/ads/`: The Ledger and its Hashing Schema.
*   `_cortex/specs/`: Architectural and Functional requirements.
*   `_cortex/work_logs/`: Human-readable summaries of sessions.
*   `_cortex/AI_PROTOCOL.md`: The rulebook for all agents.
*   `_cortex/ops/log.py`: The only tool allowed to write to the Ledger (handles locking and hashing).

---

### 5. Universal Applicability
To apply this to a new domain (e.g., Writing a Book):
1.  **Define Entities:** Identify roles (e.g., *Researcher*, *Plotter*, *Drafting Agent*).
2.  **Define Jurisdictions:** (e.g., *Plotter* edits `plot/`, *Drafting* edits `chapters/`).
3.  **Bootstrap:** Run the ADT Installer to create the Ledger and Panel.
4.  **Execute:** All agents use `log.py` to document the creative process.

---
*Created by the OceanPulse Overseer | ADT Framework (Sheridan, 2026)*
