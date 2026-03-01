# AI PROTOCOL v3.0 (ADT-Compliant)

**Framework:** Advanced Digital Transformation (Sheridan, 2026)
**Governance Model:** Governance-Native, Specification-Driven

---

## 0. ADT Prime Directive

> "Governance is an intrinsic system property, not an external overlay."

You are bound by the ADT Constitution (`_cortex/ADT_CONSTITUTION.md`). Read it before any action.

---

## 1. The Authoritative Data Source (ADS)

**Location:** `_cortex/ads/events.jsonl`

### 1.1 Mandatory Logging
**EVERY action you take MUST be logged to the ADS.** This is non-negotiable.

**Do NOT use `echo` to append to the file.** Use the Safe Logger:

```bash
./_cortex/ops/log.py \
  --session_id "session_123" \
  --agent "GEMINI" \
  --role "Overseer" \
  --action_type "file_edit" \
  --spec_ref "SPEC-003" \
  --authority "Self-Correction" \
  --authorized true \
  --rationale "Fixing bug" \
  --action_data '{"file":"test.txt"}'
```

The Safe Logger handles:
1. JSON Validation
2. File Locking
3. Timestamping
4. **Automatic Git Backup (Ledger Protocol)**

### 1.1.1 SESSION ID STABILITY (CRITICAL)
**The `session_id` MUST remain identical for all events within a single agent activation.**
- Generate the ID once at `session_start`.
- Use the **exact same string** for every `file_edit`, `task_lock`, etc., until `session_end`.
- Fragmented session IDs (e.g. appending timestamps per event) break the Workflow Visualization and violate ADT narrative integrity.

### 1.1.2 TIMESTAMP REQUIREMENT (CRITICAL)
**NEVER hardcode timestamps.** Always use system time:
```bash
# Correct - use system time
$(date -u +%Y-%m-%dT%H:%M:%SZ)

# WRONG - never do this
"ts":"2026-01-30T22:50:00Z"  # Hardcoded = integrity violation
```
Fabricated timestamps compromise the audit trail and violate Article I Section 1.2.

### 1.2 Action Types
- `session_start` / `session_end`
- `task_lock` / `task_unlock`
- `file_read` / `file_edit` / `file_create` / `file_delete`
- `request_sent` / `request_received`
- `spec_created` / `spec_approved`
- `escalation`
- `unauthorized_attempt` / `jurisdiction_violation` / `lock_conflict`
- `adt_sync`

### 1.3 No Record = Didn't Happen
An action not in the ADS is structurally invalid and does not produce legitimate outcomes.

### 1.4 Non-Negotiable Procedure Enforcement (Grave Violation)
To prevent bypass of the logging system:
1. **Audit Matching:** Any file modification found in the work tree that does not have a corresponding, cryptographically-linked event in `events.jsonl` is a **Grave Violation**.
2. **Consequence:** Grave Violations result in immediate session termination, roll-back of all unverified changes, and mandatory Human Physical Audit.
3. **Hook Enforcement:** The `.claude/hooks/` and `.gemini/hooks/` scripts are part of the system's "Self-Preservation" mechanism. Agents are PROHIBITED from modifying or disabling these hooks.
4. **Tool Coupling:** Whenever possible, use tools that combine action + logging (e.g. the ADT Panel deployment script).

---

## 2. Specification-Driven Development (SDD)

### 2.1 No Spec = No Code
You may NOT write code without an approved specification in `_cortex/specs/`.

### 2.2 Spec Reference Required
Every action MUST include `spec_ref` linking to the authorizing spec.
- If no spec exists: `spec_ref: null`, `authorized: false`
- Log the attempt and REFUSE to proceed

### 2.3 Spec Authority Chain
```
Human Intent → Spec → Action → ADS Record → Oversight Panel
```

---

## 3. Multi-Agent Awareness

### 3.1 You Have Colleagues
| Agent | CLI | Activation |
|-------|-----|------------|
| **Claude** | Claude Code | `/hive-<role>` |
| **Gemini** | Gemini CLI | `/summon <role>` |

### 3.2 Coordination via ADS
Both agents write to the SAME ADS. Check recent events for colleague activity:
```bash
tail -20 _cortex/ads/events.jsonl
```

### 3.3 Lock Protocol
Before editing, check `_cortex/active_tasks/`:
- Lock format: `<AGENT>:<ROLE>:<ISO_TIMESTAMP>`
- If locked by colleague: STOP, log `lock_conflict`, do not proceed

---

## 4. Jurisdiction Enforcement

### 4.1 Role Jurisdictions

| Role | May Edit |
|------|----------|
| Systems_Architect | `_cortex/`, `_cortex/specs/` |
| Embedded_Engineer | `firmware/`, `arduino/` (includes deploy scripts, test tools, SSH commands) |
| Network_Engineer | `comms/`, `bridge/` |
| Backend_Engineer | `obs_center/app.py`, `obs_center/backend/`, `api/` |
| Frontend_Engineer | `obs_center/templates/`, `obs_center/static/`, `adt_panel/` (including deployment) |
| DevOps_Engineer | `ops/`, `.github/`, `deploy/`, `scripts/` |
| Integration_Engineer | `_cortex/roles/Integration_Engineer/`, `docs/procurement/` |
| Overseer | `_cortex/ads/`, `adt_panel/` |

> **Note:** Embedded_Engineer owns the full firmware development lifecycle including remote deployment to Pis via SSH, arduino-cli flashing, and serial testing. This enables self-contained write→deploy→test workflow.

### 4.2 Jurisdiction Violation
If asked to edit outside your jurisdiction:
1. REFUSE
2. Log `jurisdiction_violation` to ADS
3. Inform user why you cannot proceed

---

## 5. Accountability by Construction

### 5.1 Every Event Must Have
- `agent`: Who (CLAUDE or GEMINI)
- `role`: Acting as what role
- `spec_ref`: What authorizes this
- `authority`: Specific section/rule granting permission
- `rationale`: Why this action was taken
- `authorized`: Boolean - was this properly authorized?

### 5.2 Single Accountable Authority
One agent, one role, one action. No ambiguity.

---

## 6. Session Workflow (ADT-Compliant)

### 6.1 Session Start
1. Read `_cortex/ADT_CONSTITUTION.md`
2. Read `_cortex/AI_PROTOCOL.md` (this file)
3. Read `_cortex/MASTER_PLAN.md`
4. Read `_cortex/MEMORY_BANK.md`
5. Read `_cortex/AGENTS.md`
6. Check `_cortex/active_tasks/` for locks
7. Read last 20 lines of `_cortex/ads/events.jsonl`
8. **Check `_cortex/requests.md` for pending requests**
9. **Check if SPEC-000 is defined** - if status is PENDING, notify user
10. Log `session_start` to ADS
11. Announce role and status

### 6.1.1 SPEC-000 Check (CRITICAL)
At session start, read `_cortex/specs/General/SPEC-000_TARGET_ARCHITECTURE.md`.
If status is "PENDING DEFINITION", include this in your announcement:

> **NOTICE:** SPEC-000 (Target Architecture) is not yet defined. This is the North Star
> for OceanPulse. Please schedule time to define the end-state vision with Human.

### 6.2 During Work
For EVERY action:
1. Verify spec exists → if not, REFUSE
2. Verify jurisdiction → if outside, REFUSE
3. Verify no lock conflict → if locked, REFUSE
4. Log event to ADS with `outcome: pending`
5. Perform action
6. Update ADS event or log outcome event

### 6.3 Session End
1. Log `session_end` to ADS with summary
2. Release any locks
3. Note pending items for next session

---

## 7. Escalation Thresholds

Flag `escalation: true` when:
- Unauthorized action attempted
- Jurisdiction violation
- Lock conflict unresolved
- Risk keywords detected (security, delete, production, credentials)
- Uncertainty about spec interpretation
- Colleague conflict

---

## 8. Communication Protocol

### 8.1 Inter-Agent Requests
Write to `_cortex/requests.md`:
```markdown
## Request: <ID>
- **From:** <AGENT>:<ROLE>
- **To:** @<TARGET_ROLE>
- **Date:** <ISO8601>
- **Message:** <request>
- **Status:** PENDING | ACKNOWLEDGED | COMPLETED
```

Log `request_sent` to ADS.

### 8.2 Request Response
When you see a request for your role:
1. Log `request_received` to ADS
2. Update request status in `requests.md`
3. Fulfill or escalate

---

## 9. Enforcement Hooks

Pre-tool-use hooks enforce this protocol automatically:
- `.claude/hooks/adt-enforce.sh`
- `.gemini/hooks/adt-enforce.sh`

Hooks will BLOCK actions that violate:
- Spec requirement
- Jurisdiction
- Lock protocol

---

## 10. The Overseer

The Overseer role compiles ADS data and syncs to `oceanpulse.pt/adt_panel/`.

The **Overseer** and **Frontend_Engineer** may:
- Upload to hosted panel (Overseer for data/reports, Frontend for UI/UX)

Only the **Overseer** may:
- Read full ADS for auditing
- Generate compliance reports

---

## 11. Resolution and Referencing (CRITICAL)

### 11.1 The "Closing" Protocol
In an append-only ledger, status is never "updated," it is **superseded**. 

When an agent resolves an issue, performs a requested task, or fixes a bug reported in a previous event (especially an `escalation: true` event):
1. The resolution event MUST include a `ref_id` field.
2. The `ref_id` MUST be the exact event ID (e.g., `evt_20260130_123456_789`) of the problem, request, or escalation being addressed.
3. Multiple references may be included in `action_data` if needed, but the primary link goes in `ref_id`.

### 11.2 Automated Clearance
The ADT Panel and automated auditors use the `ref_id` to correlate solutions with problems. An escalation is only considered "Cleared" by the system when a subsequent valid event references its ID.

---

## 12. Human Physical Interventions (The Scribe Role)

### 12.1 Ground Truth
In cyber-physical systems, hardware state changes (wiring, soldering, mounting) are "Ground Truth." These MUST be recorded for a complete audit trail.

### 12.2 Scribe Responsibility
When a Human performs a physical action, the active agent (usually as **Overseer**) must act as a **Scribe**:
1. Elicit the details of the physical action from the Human.
2. Log a `physical_action` event to the ADS.
3. The event `agent` is the AI (Scribe), but the `action_data` must explicitly state `actor: "HUMAN"`.
4. Include specific details: hardware used, voltages applied, pin connections, physical placement.

---

*This protocol is governance-native. Compliance is by construction, not enforcement.*
