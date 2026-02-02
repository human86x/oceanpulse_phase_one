# Active AI Agents

This project uses **two AI systems** working as colleagues in a shared workspace.

## The Team

| Agent | CLI | Activation | Strengths |
|-------|-----|------------|-----------|
| **Claude** | Claude Code | `/hive-<role>` | Code editing, refactoring, complex reasoning |
| **Gemini** | Gemini CLI | `/summon <role>` | Speckit workflow, planning, task breakdown |

## How They Coordinate

Both agents use the **same** coordination system:

```
_cortex/
├── active_tasks/     # Lock files prevent conflicts
├── work_logs/        # Session logs show who did what
├── requests.md       # Inter-agent communication
└── MASTER_PLAN.md    # Shared objectives
```

## Lock File Convention

When an agent starts work:
```
File: _cortex/active_tasks/<task_name>.lock
Content: <SYSTEM>:<ROLE>:<ISO_TIMESTAMP>

Example:
CLAUDE:Frontend_Engineer:2026-01-30T19:30:00Z
GEMINI:Backend_Engineer:2026-01-30T18:45:00Z
```

## Work Log Convention

Each session appends to: `_cortex/work_logs/<YYYY-MM-DD>_<role>.md`

```markdown
## Session: <SYSTEM> | <TIME>

### Completed
- Item 1
- Item 2

### Pending
- Item for next session

### Requests
- @<Role>: Description
```

## Rules of Engagement

1. **Check locks first** - Never work on a locked task
2. **Read recent logs** - Know what your colleague did
3. **Respect their work** - Don't undo without user approval
4. **Communicate via requests.md** - Tag the role you need
5. **Log your work** - Your colleague needs context too
