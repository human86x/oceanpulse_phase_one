#!/bin/bash
# tailscale_watchdog.sh — OceanPulse Tailscale Connectivity Watchdog
# Runs via cron every 5 minutes on each Pi.
# If Tailscale is down or disconnected, restarts the service.
# Logs actions to syslog for traceability.
#
# SPEC-REF: SPEC-022 (Lab Center Connectivity), SPEC-000 (Target Architecture)
# JURISDICTION: DevOps_Engineer — ops/

TAG="tailscale-watchdog"
MAX_RETRIES=3
RETRY_DELAY=10

log() {
    logger -t "$TAG" "$1"
}

# 1. Check if tailscaled is running
if ! systemctl is-active --quiet tailscaled; then
    log "ALERT: tailscaled not running. Starting service..."
    sudo systemctl start tailscaled
    sleep 5
    if systemctl is-active --quiet tailscaled; then
        log "OK: tailscaled started successfully."
    else
        log "CRITICAL: Failed to start tailscaled. Manual intervention required."
        exit 1
    fi
fi

# 2. Check Tailscale connection status
TS_STATUS=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('BackendState',''))" 2>/dev/null)

if [ "$TS_STATUS" = "Running" ]; then
    exit 0
fi

log "ALERT: Tailscale state is '$TS_STATUS' (expected 'Running'). Attempting recovery..."

# 3. If NeedsLogin or NoState, try bringing it up
for i in $(seq 1 $MAX_RETRIES); do
    log "Recovery attempt $i/$MAX_RETRIES..."

    if [ "$TS_STATUS" = "NeedsLogin" ]; then
        log "Tailscale needs re-authentication. Running 'tailscale up'..."
        sudo tailscale up --accept-routes --ssh 2>&1 | while read -r line; do
            log "tailscale up: $line"
        done
    elif [ "$TS_STATUS" = "Stopped" ] || [ -z "$TS_STATUS" ]; then
        log "Tailscale stopped or unknown state. Restarting service..."
        sudo systemctl restart tailscaled
        sleep 5
        sudo tailscale up --accept-routes --ssh 2>&1 | while read -r line; do
            log "tailscale up: $line"
        done
    else
        log "Unexpected state '$TS_STATUS'. Restarting tailscaled..."
        sudo systemctl restart tailscaled
        sleep 5
    fi

    sleep "$RETRY_DELAY"

    # Re-check
    TS_STATUS=$(tailscale status --json 2>/dev/null | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('BackendState',''))" 2>/dev/null)

    if [ "$TS_STATUS" = "Running" ]; then
        log "OK: Tailscale recovered on attempt $i."
        exit 0
    fi
done

log "CRITICAL: Tailscale failed to recover after $MAX_RETRIES attempts. State: '$TS_STATUS'. Manual intervention required."
exit 1
