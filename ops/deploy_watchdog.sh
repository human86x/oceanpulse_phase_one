#!/bin/bash
# deploy_watchdog.sh — Deploy Tailscale watchdog to all OceanPulse Pis
# Copies tailscale_watchdog.sh and installs a cron job (every 5 min).
#
# SPEC-REF: SPEC-022, SPEC-000
# JURISDICTION: DevOps_Engineer — ops/

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WATCHDOG="$SCRIPT_DIR/tailscale_watchdog.sh"
REMOTE_PATH="/usr/local/bin/tailscale_watchdog.sh"
CRON_ENTRY="*/5 * * * * $REMOTE_PATH >/dev/null 2>&1"

# All Pis: user@tailscale_ip
TARGETS=(
    "lab@100.115.88.91"        # System A - Main Mission
    "router@100.116.100.92"    # System B - Health/Router
    "node1@100.64.151.40"      # System C - Onshore Gateway
    "lab@100.77.91.123"        # System D - Lab Center
)

PASS="777"

for TARGET in "${TARGETS[@]}"; do
    HOST=$(echo "$TARGET" | cut -d@ -f2)
    USER=$(echo "$TARGET" | cut -d@ -f1)

    echo "--- Deploying to $TARGET ---"

    # Check reachability
    if ! ping -c 1 -W 3 "$HOST" >/dev/null 2>&1; then
        echo "  SKIP: $HOST unreachable"
        continue
    fi

    # Copy watchdog script
    sshpass -p "$PASS" scp -o StrictHostKeyChecking=no "$WATCHDOG" "$TARGET:/tmp/tailscale_watchdog.sh" 2>/dev/null

    # Install and set up cron
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no "$TARGET" bash -s <<REMOTE_EOF
        sudo cp /tmp/tailscale_watchdog.sh $REMOTE_PATH
        sudo chmod +x $REMOTE_PATH
        rm /tmp/tailscale_watchdog.sh

        # Add cron job if not already present
        if ! crontab -l 2>/dev/null | grep -q "tailscale_watchdog"; then
            (crontab -l 2>/dev/null; echo "$CRON_ENTRY") | crontab -
            echo "  Cron installed."
        else
            echo "  Cron already exists."
        fi

        echo "  Watchdog deployed to $REMOTE_PATH"
REMOTE_EOF

    echo "  DONE: $TARGET"
done

echo ""
echo "=== Deployment complete ==="
