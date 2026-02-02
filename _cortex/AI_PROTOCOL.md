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

Before ANY file edit, you MUST append an event:
```jsonl
{"id":"evt_YYYYMMDD_HHMMSS_XXX","ts":"<ISO8601>","session_id":"<session>","agent":"CLAUDE|GEMINI","role":"<your_role>","action_type":"<type>","spec_ref":"<SPEC-XXX>","authority":"<what authorizes this>","authorized":true|false,"rationale":"<why>","action_data":{...},"outcome":"pending","escalation":false}
```

### 1.1.1 TIMESTAMP REQUIREMENT (CRITICAL)
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

*This protocol is governance-native. Compliance is by construction, not enforcement.*
