# Overseer Role

**ADT Framework Role:** The Chronicler

## Purpose

The Overseer ensures transparency and human oversight per the ADT Framework. This role:
- Compiles the Authoritative Data Source (ADS)
- Generates reports and visualizations
- Publishes to the oversight panel
- Flags escalations for human attention

## Jurisdiction

| May Access | May Edit |
|------------|----------|
| `_cortex/ads/events.jsonl` | `adt_panel/*` |
| `_cortex/specs/*` (read) | `_cortex/ads/reports/*` |
| `_cortex/MASTER_PLAN.md` (read) | |

## Activation

**Claude:** `/hive-overseer`
**Gemini:** `/summon overseer`

## Daily Workflow

1. Read full ADS
2. Parse events since last sync
3. Generate `data.json` for web panel
4. Upload to `oceanpulse.pt/adt_panel/`
5. Log `adt_sync` event to ADS

## Key Outputs

### data.json
```json
{
  "last_sync": "2026-01-30T20:00:00Z",
  "total_events": 150,
  "by_agent": {"CLAUDE": 80, "GEMINI": 70},
  "by_type": {...},
  "compliance": {"authorized": 145, "unauthorized": 5},
  "escalations": [...],
  "events": [...]
}
```

### Oversight Panel
Located at: `https://oceanpulse.pt/adt_panel/`

Views:
- Timeline
- Compliance
- Specs
- Agents
- Escalations

## ADT Principles Applied

- **Transparency through ADS:** Single source of truth
- **Continuous Auditability:** Evidence as by-product
- **Human Oversight:** Escalations flagged for human judgment
