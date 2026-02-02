# SPEC-003: ADT Operational Dashboard

**Author:** CLAUDE (Systems_Architect)
**Date:** 2026-01-30
**Revised:** 2026-02-01 (v2.0 - Delegation Tree)
**Status:** APPROVED
**Supersedes:** None (Extends existing ADT Panel)

> **v2.0 Changes:** Replaced simple "Delegation Map" matrix with interactive "Delegation Tree"
> showing full authority flow. Added delegation tracking to task schema. Matrix retained as
> summary view alongside tree.

---

## 1. Problem Statement

The current ADT Panel (`adt_panel/`) is an **audit dashboard** focused on event history and compliance metrics. While valuable for governance verification, it lacks **operational management** capabilities:

| Current Panel Has | Missing (User Requested) |
|-------------------|--------------------------|
| Event timeline | Task/TODO list |
| Compliance gauge | Hierarchical project view |
| Agent activity | **Delegation Tree** (authority flow) |
| Spec reference counts | Progress tracking |

Users cannot see:
- What needs to be done
- Who is responsible for what
- How work relates to specs and phases
- Overall project progress
- **Who delegated what to whom** (authority chains)
- **Traceability from task back to authorizing spec**

---

## 2. Proposed Solution

Enhance the ADT Panel with three new views:

### 2.1 Task Board (TODO List)

A kanban-style board showing tasks by status:

```
┌─────────────┬─────────────┬─────────────┐
│   PENDING   │ IN PROGRESS │  COMPLETED  │
├─────────────┼─────────────┼─────────────┤
│ [Task 1]    │ [Task 3]    │ [Task 5]    │
│ @Backend    │ @Embedded   │ @Architect  │
│ SPEC-002    │ SPEC-002    │ SPEC-001    │
├─────────────┼─────────────┼─────────────┤
│ [Task 2]    │ [Task 4]    │             │
│ @Frontend   │ @Network    │             │
│ SPEC-001    │ SPEC-002    │             │
└─────────────┴─────────────┴─────────────┘
```

**Task Card Shows:**
- Task title
- Assigned role (@Role)
- Linked spec (SPEC-XXX)
- Agent working on it (Claude/Gemini badge)
- Created date
- Priority indicator

### 2.2 Hierarchy View (Project Structure)

Tree view showing project → phases → specs → tasks:

```
OceanPulse
├── Phase 1: Prototype Validation
│   ├── SPEC-001: Observational Center
│   │   ├── [✓] Backend API routes
│   │   ├── [→] Frontend dashboard
│   │   └── [ ] WebSocket integration
│   │
│   ├── SPEC-002: Hardware Integration
│   │   ├── [✓] TDS sensor validation
│   │   ├── [→] Serial bridge implementation
│   │   └── [ ] LoRa module setup
│   │
│   └── SPEC-003: ADT Dashboard (this spec)
│       └── [ ] Panel implementation
│
└── Phase 2: Field Deployment (future)
```

**Indicators:**
- `[ ]` Pending
- `[→]` In Progress
- `[✓]` Completed
- `[!]` Blocked/Escalated

### 2.3 Delegation Tree (Authority Flow Visualization)

An interactive tree showing **who delegated what to whom**, enabling full traceability from spec creation through task completion.

#### 2.3.1 Tree View (Primary)

Clickable tree showing delegation chains:

```
SPEC-002: Component Integration
└── Created by: Systems_Architect (CLAUDE)
    │
    ├── → Embedded_Engineer
    │   ├── task_001: TDS Sensor Validation (GEMINI) ● IN_PROGRESS
    │   │   └── [subtask] Calibrate sensor readings
    │   └── task_003: Relay Control (GEMINI) ● IN_PROGRESS
    │
    ├── → Network_Engineer
    │   ├── task_002: Serial Bridge (GEMINI) ✓ COMPLETED
    │   └── task_004: LoRa Integration ○ PENDING
    │       └── → delegated to: (unassigned)
    │
    └── → Frontend_Engineer
        └── task_008: Dual-Circuit Control ○ PENDING
```

**Tree Node Types:**
- **Spec Node:** Root of delegation chain, shows author
- **Role Node:** Who received delegation
- **Task Node:** Individual work item with status indicator
- **Subtask Node:** Further breakdown (if role sub-delegates)

**Status Indicators:**
- `○` Pending
- `●` In Progress
- `✓` Completed
- `!` Blocked/Escalated

**Interactions:**
- Click any node to expand/collapse children
- Click task to see full details + ADS event history
- Click role to see all tasks delegated to that role
- Trace upward to find authorizing spec and delegator

#### 2.3.2 Summary Matrix (Secondary)

Compact overview showing task counts per role × agent:

```
                    CLAUDE    GEMINI    UNASSIGNED
┌──────────────────┬─────────┬─────────┬───────────┐
│ Systems_Architect│    2    │    1    │     0     │
│ Embedded_Engineer│    0    │    3    │     1     │
│ Network_Engineer │    0    │    2    │     0     │
│ Backend_Engineer │    1    │    1    │     0     │
│ Frontend_Engineer│    0    │    0    │     2     │
│ DevOps_Engineer  │    0    │    0    │     0     │
└──────────────────┴─────────┴─────────┴───────────┘
```

- Color-coded by workload (green/yellow/red)
- Click cell to filter Tree View by that role+agent
- Tooltip shows (completed/in_progress/pending) breakdown

---

## 3. Data Model

### 3.1 New File: `_cortex/tasks.json`

```json
{
  "schema_version": "2.0",
  "last_updated": "2026-02-01T00:00:00Z",
  "tasks": [
    {
      "id": "task_001",
      "title": "Implement Serial Bridge on Pi 5",
      "description": "Create Python bridge between Arduino Mega and LoRa module",
      "status": "in_progress",
      "priority": "high",
      "spec_ref": "SPEC-002",
      "phase": "1",

      "delegation": {
        "delegated_by": {
          "role": "Systems_Architect",
          "agent": "CLAUDE"
        },
        "delegated_to": {
          "role": "Network_Engineer",
          "agent": "GEMINI"
        },
        "delegated_at": "2026-01-30T20:45:00Z"
      },

      "created_by": "Systems_Architect",
      "created_at": "2026-01-30T20:45:00Z",
      "updated_at": "2026-01-30T22:00:00Z",
      "completed_at": null,

      "blocked_by": [],
      "subtasks": [
        {
          "id": "task_001_sub_001",
          "title": "Sub-delegated task example",
          "delegation": {
            "delegated_by": {
              "role": "Network_Engineer",
              "agent": "GEMINI"
            },
            "delegated_to": {
              "role": "DevOps_Engineer",
              "agent": null
            },
            "delegated_at": "2026-01-30T21:00:00Z"
          }
        }
      ]
    }
  ]
}
```

**Delegation Fields (v2.0):**

| Field | Type | Description |
|-------|------|-------------|
| `delegation.delegated_by.role` | string | Role that assigned this task |
| `delegation.delegated_by.agent` | string | Agent (CLAUDE/GEMINI) that assigned |
| `delegation.delegated_to.role` | string | Role receiving the task |
| `delegation.delegated_to.agent` | string/null | Agent assigned (null = unassigned) |
| `delegation.delegated_at` | ISO8601 | When delegation occurred |
| `subtasks` | array | Nested tasks if role sub-delegates |

This enables:
- **Upward tracing:** From any task → who delegated → authorizing spec
- **Downward tracing:** From spec → all delegated roles → all tasks
- **Sub-delegation:** Roles can break down work and delegate further

### 3.2 New File: `_cortex/phases.json`

```json
{
  "phases": [
    {
      "id": "1",
      "name": "Prototype Validation",
      "status": "active",
      "specs": ["SPEC-001", "SPEC-002", "SPEC-003"]
    },
    {
      "id": "2",
      "name": "Field Deployment",
      "status": "planned",
      "specs": []
    }
  ]
}
```

### 3.3 ADS Integration

Task state changes are logged to `events.jsonl`:

```jsonl
{"action_type": "task_created", "action_data": {"task_id": "task_001", ...}}
{"action_type": "task_status_change", "action_data": {"task_id": "task_001", "from": "pending", "to": "in_progress"}}
{"action_type": "task_assigned", "action_data": {"task_id": "task_001", "role": "Network_Engineer", "agent": "GEMINI"}}
```

---

## 4. Panel UI Changes

### 4.1 Navigation Tabs

Add tabs to the panel header:

```
[Timeline] [Task Board] [Hierarchy] [Delegation] [Settings]
```

### 4.2 Task Board View (`views/taskboard.js`)

- Three columns: Pending | In Progress | Completed
- Drag-and-drop disabled (status changes via ADS only)
- Filter by: Role, Agent, Spec, Priority
- Click card to expand details

### 4.3 Hierarchy View (`views/hierarchy.js`)

- Collapsible tree structure
- Click to expand phases → specs → tasks
- Progress bar per spec (tasks completed / total)
- Click task to see details

### 4.4 Delegation View (`views/delegation.js`)

**Two-panel layout:**

#### Left Panel: Delegation Tree
- Collapsible tree rooted at specs
- Shows: Spec → Delegator → Role → Tasks → Subtasks
- Click to expand/collapse branches
- Status icons on task nodes (○ ● ✓ !)
- Click task to show details in modal
- Breadcrumb trail showing current path

#### Right Panel: Summary Matrix
- Role × Agent count matrix
- Color-coded cells: green (<3), yellow (3-5), red (>5)
- Click cell to filter tree to that role+agent
- Tooltip shows (completed/in_progress/pending)

#### Interactions
- Tree node click → expand/collapse
- Task click → detail modal with ADS history
- Matrix cell click → filter tree
- "Trace Authority" button → highlights path to spec root
- Export delegation report (PDF/CSV)

---

## 5. Implementation Jurisdiction

| Component | Responsible Role |
|-----------|------------------|
| `_cortex/tasks.json` | Systems_Architect (create structure) |
| `_cortex/phases.json` | Systems_Architect (create structure) |
| `adt_panel/views/*.js` | Frontend_Engineer OR Overseer |
| `adt_panel/index.html` | Frontend_Engineer OR Overseer |
| Task CRUD operations | All roles (via ADS logging) |
| Panel deployment | Overseer (sync to oceanpulse.pt) |

---

## 6. ADT Compliance

This spec maintains ADT principles:

1. **Single Source of Truth:** Tasks stored in `_cortex/tasks.json`, changes logged to ADS
2. **Traceability:** Every task links to a spec_ref AND records full delegation chain
3. **Accountability:** Every task has `delegated_by` and `delegated_to` with role+agent
4. **Governance by Construction:** Task status changes require ADS events
5. **Authority Flow:** Delegation Tree enables visual tracing from any task back to authorizing spec and original delegator (supports ADT Article III Section 3.3)

---

## 7. Acceptance Criteria

### Data Model
- [ ] `_cortex/tasks.json` upgraded to schema v2.0 with delegation fields
- [ ] `_cortex/phases.json` created with Phase 1 data
- [ ] All existing tasks migrated to include `delegation` object

### Panel Views
- [ ] Panel has 4 navigation tabs (Timeline, Task Board, Hierarchy, Delegation)
- [ ] Task Board shows tasks in 3 columns by status
- [ ] Hierarchy view shows Project → Phase → Spec → Task tree

### Delegation Tree (Primary Focus)
- [ ] Tree view shows Spec → Delegator → Role → Task hierarchy
- [ ] Nodes are expandable/collapsible
- [ ] Task nodes show status indicators (○ ● ✓ !)
- [ ] Clicking task shows detail modal with ADS event history
- [ ] Subtasks display under parent tasks (sub-delegation)
- [ ] "Trace Authority" highlights path from task to spec root

### Summary Matrix
- [ ] Role × Agent matrix displays alongside tree
- [ ] Cells color-coded by workload (green/yellow/red)
- [ ] Clicking cell filters tree to that role+agent
- [ ] Tooltip shows (completed/in_progress/pending) breakdown

### ADT Compliance
- [ ] All task delegations logged to ADS with `action_type: task_delegated`
- [ ] Delegation changes create new ADS events (not edits)
- [ ] Panel deployed to oceanpulse.pt/adt_panel/

---

## 8. Approval

**Human Approval Required:** YES

~~This spec changes the ADT governance tooling. Implementation should not proceed until human approves this design.~~

**APPROVED:** 2026-02-01 by Human

---

*Spec created by CLAUDE (Systems_Architect) per ADT Constitution Article II*
