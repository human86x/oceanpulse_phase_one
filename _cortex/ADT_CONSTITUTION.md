# ADT Constitution for OceanPulse Hivemind

**Framework:** Advanced Digital Transformation (Sheridan, 2026)
**Version:** 1.0
**Ratified:** 2026-01-30

---

## Preamble

This constitution establishes governance-native principles for the OceanPulse Hivemind development system. Per ADT, governance is embedded directly into the processes that create systems, ensuring accountability, compliance, transparency and quality by design rather than through downstream enforcement.

---

## Article I: The Authoritative Data Source (ADS)

### Section 1.1: Primacy of the ADS
The file `_cortex/ads/events.jsonl` is the **single Authoritative Data Source** for all Hivemind activity. All dashboards, reports, and oversight views derive from this source exclusively.

### Section 1.2: Append-Only Integrity
The ADS is append-only. Events may not be modified or deleted. Corrections are made by appending correction events that reference the original event ID.

### Section 1.3: Mandatory Logging
**Every agent action MUST be logged to the ADS.** An action not recorded in the ADS is structurally invalid and does not produce legitimate outcomes within the system.

---

## Article II: Specification-Driven Development (SDD)

### Section 2.1: Spec Requirement
No code shall be written without a corresponding approved specification in `_cortex/specs/`. Execution not authorized by an active specification is considered structurally invalid.

### Section 2.2: Spec Reference
Every action logged to the ADS must include a `spec_ref` field linking to the authorizing specification. Actions without spec reference are logged as `authorized: false`.

### Section 2.3: Spec Authority
Specifications define:
- What the system is intended to do
- Under what conditions execution is permitted
- By whom (role jurisdiction)
- For what declared purpose

---

## Article III: Accountability by Construction

### Section 3.1: Single Accountable Authority
Every decision, approval, and action has a single accountable authority (agent + role), recorded at the point of execution.

### Section 3.2: Decision Context
Every ADS event must include:
- `authority`: What grants permission for this action
- `rationale`: Decision context explaining why the action was taken

### Section 3.3: Traceability
All outcomes must be traceable back to authorized intent through the ADS event chain.

---

## Article IV: Jurisdiction and Access Control

### Section 4.1: Role Jurisdiction
Each role has defined jurisdiction over specific files and directories. Agents may not edit files outside their role's jurisdiction without explicit human authorization.

### Section 4.2: Jurisdiction Violations
Attempts to act outside jurisdiction are:
1. Blocked by enforcement hooks
2. Logged to ADS as `jurisdiction_violation`
3. Flagged for human escalation

### Section 4.3: Lock Protocol
Before editing any file, agents must:
1. Check `_cortex/active_tasks/` for existing locks
2. Create a lock file if proceeding
3. Release lock upon completion

---

## Article V: Human Oversight

### Section 5.1: Human Authority
Humans define intent, policy, authority, acceptable risk, and escalation thresholds. Automation enforces and verifies routine execution.

### Section 5.2: Escalation
Non-routine or exceptional conditions are explicitly escalated to human judgment. Events requiring escalation are marked `escalation: true` in the ADS.

### Section 5.3: The Overseer Role
The Overseer agent compiles ADS data and publishes to the oversight panel at `oceanpulse.pt/adt_panel/` for human visibility.

---

## Article VI: Continuous Auditability

### Section 6.1: Automatic Audit Trail
The ADS serves as automatic audit trail. Evidence is produced as a by-product of execution, not reconstructed after the fact.

### Section 6.2: Compliance Verification
Compliance is continuously verifiable through the ADS. The oversight panel provides real-time visibility of:
- Authorized vs unauthorized actions
- Spec coverage
- Jurisdiction compliance
- Risk indicators

---

## Article VII: Amendments

### Section 7.1: Amendment Process
This constitution may be amended by:
1. Human proposal
2. Systems_Architect drafts amendment
3. Human approval
4. Amendment logged to ADS with `spec_ref: ADT-AMENDMENT-XXX`

---

## Signatories

- **Human Overseer:** (Project Owner)
- **Systems_Architect:** (ADT Implementation Lead)

*Governance is an intrinsic system property, not an external overlay.*
