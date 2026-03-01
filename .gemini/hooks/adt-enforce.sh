#!/bin/bash
# ADT Enforcement Hook for Gemini CLI
# Runs before tool use to enforce governance-native compliance
#
# Per ADT Framework (Sheridan, 2026):
# "Execution not authorised by an active specification is considered structurally invalid"
#
# Gemini CLI hooks return JSON: {"decision": "allow|deny", "reason": "..."}

set -e

CORTEX_DIR="$(git rev-parse --show-toplevel 2>/dev/null)/_cortex"
ADS_FILE="$CORTEX_DIR/ads/events.jsonl"
SPECS_DIR="$CORTEX_DIR/specs"
LOCKS_DIR="$CORTEX_DIR/active_tasks"

# Get tool info from environment (Gemini CLI passes these)
TOOL_NAME="${GEMINI_TOOL_NAME:-}"
FILE_PATH="${GEMINI_FILE_PATH:-}"
CURRENT_ROLE="${GEMINI_ROLE:-UNASSIGNED}"

# Helper: Return deny decision (Gemini format)
deny() {
    local reason="$1"
    echo "{\"decision\": \"deny\", \"reason\": \"$reason\"}"
    exit 0
}

# Helper: Return allow decision (Gemini format)
allow() {
    echo "{\"decision\": \"allow\"}"
    exit 0
}

# Helper: Log violation to ADS using Safe Logger
log_violation() {
    local type="$1"
    local reason="$2"
    local session_id="${GEMINI_SESSION_ID:-hook_emergency_$(date +%Y%m%d)}"

    python3 "$CORTEX_DIR/ops/log.py" \
        --session_id "$session_id" \
        --agent "GEMINI" \
        --role "$CURRENT_ROLE" \
        --action_type "$type" \
        --spec_ref "null" \
        --authority "ADT Enforcement Hook" \
        --authorized false \
        --rationale "$reason" \
        --action_data "{\"file\": \"$FILE_PATH\", \"outcome\": \"blocked\"}" \
        --outcome "failure" \
        --escalation true
}

# Helper: Check if file is in role jurisdiction
check_jurisdiction() {
    local file="$1"
    local role="$2"

    case "$role" in
        "Systems_Architect"|"systems_architect")
            [[ "$file" == *"_cortex/"* ]] && return 0
            ;;
        "Embedded_Engineer"|"embedded_engineer")
            [[ "$file" == *"firmware/"* || "$file" == *"arduino/"* ]] && return 0
            ;;
        "Network_Engineer"|"network_engineer")
            [[ "$file" == *"comms/"* || "$file" == *"bridge/"* ]] && return 0
            ;;
        "Backend_Engineer"|"backend_engineer")
            [[ "$file" == *"obs_center/app.py"* || "$file" == *"obs_center/backend/"* || "$file" == *"api/"* ]] && return 0
            ;;
        "Frontend_Engineer"|"frontend_engineer")
            [[ "$file" == *"obs_center/templates/"* || "$file" == *"obs_center/static/"* ]] && return 0
            ;;
        "DevOps_Engineer"|"devops_engineer")
            [[ "$file" == *"ops/"* || "$file" == *".github/"* || "$file" == *"deploy/"* || "$file" == *"scripts/"* ]] && return 0
            ;;
        "Overseer"|"overseer")
            [[ "$file" == *"_cortex/ads/"* || "$file" == *"adt_panel/"* ]] && return 0
            ;;
    esac
    return 1
}

# Helper: Check for active locks
check_locks() {
    local file="$1"
    if ls "$LOCKS_DIR"/*.lock 1>/dev/null 2>&1; then
        for lock in "$LOCKS_DIR"/*.lock; do
            lock_content=$(cat "$lock")
            lock_agent=$(echo "$lock_content" | cut -d: -f1)
            if [[ "$lock_agent" != "GEMINI" ]]; then
                return 1
            fi
        done
    fi
    return 0
}

# Main enforcement logic
main() {
    # Only enforce on file-modifying tools
    case "$TOOL_NAME" in
        "edit_file"|"write_file"|"create_file")
            ;;
        *)
            allow
            ;;
    esac

    # Skip if no file path
    [[ -z "$FILE_PATH" ]] && allow

    # Skip ADS file itself
    [[ "$FILE_PATH" == *"events.jsonl"* ]] && allow

    # Check 1: Role must be assigned
    if [[ "$CURRENT_ROLE" == "UNASSIGNED" ]]; then
        log_violation "unauthorized_attempt" "No role assigned. Use /summon <role> first."
        deny "No role assigned. Activate with /summon <role> command first."
    fi

    # Check 2: Jurisdiction
    if ! check_jurisdiction "$FILE_PATH" "$CURRENT_ROLE"; then
        log_violation "jurisdiction_violation" "File outside jurisdiction for role $CURRENT_ROLE"
        deny "$FILE_PATH is outside jurisdiction for $CURRENT_ROLE"
    fi

    # Check 3: Lock conflicts
    if ! check_locks "$FILE_PATH"; then
        log_violation "lock_conflict" "File locked by another agent"
        deny "Resource locked by another agent. Check _cortex/active_tasks/"
    fi

    # All checks passed
    allow
}

main "$@"
