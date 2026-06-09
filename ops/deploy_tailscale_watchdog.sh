#!/bin/bash
# deploy_tailscale_watchdog.sh — Deploy Tailscale Watchdog to all OceanPulse systems
# Copies the watchdog script + systemd service/timer, enables on boot.
#
# Usage: ./deploy_tailscale_watchdog.sh [system]
#   system: a, b, c, d, all (default: all)
#
# SPEC-REF: SPEC-022, User directive (Tailscale auto-recovery)
# JURISDICTION: DevOps_Engineer — ops/

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS="$SCRIPT_DIR/secrets.env"
if [ ! -f "$SECRETS" ]; then
    echo "ERROR: $SECRETS not found. Copy ops/secrets.env.example and fill it in." >&2
    exit 1
fi
set -a; . "$SECRETS"; set +a
: "${OP_PI_SSH_PASS:?OP_PI_SSH_PASS missing in secrets.env}"

WATCHDOG_SCRIPT="$SCRIPT_DIR/tailscale_watchdog.sh"
SERVICE_FILE="$SCRIPT_DIR/tailscale-watchdog.service"
TIMER_FILE="$SCRIPT_DIR/tailscale-watchdog.timer"

# System map: name user@host
declare -A SYSTEMS=(
    [a]="lab@100.115.88.91"
    [b]="router@100.116.100.92"
    [c]="node1@100.64.151.40"
    [d]="lab@100.77.91.123"
)

declare -A SYSTEM_NAMES=(
    [a]="System A (Main Pi)"
    [b]="System B (Health Pi)"
    [c]="System C (Gateway)"
    [d]="System D (Lab Center)"
)

SSH_OPTS="-o ConnectTimeout=10 -o StrictHostKeyChecking=no -o PreferredAuthentications=password -o PubkeyAuthentication=no"

deploy_to() {
    local key="$1"
    local target="${SYSTEMS[$key]}"
    local name="${SYSTEM_NAMES[$key]}"

    echo "========================================"
    echo "Deploying to $name ($target)"
    echo "========================================"

    # 1. Create remote directory
    echo "[1/5] Creating /opt/oceanpulse/ops/ ..."
    sshpass -p "$OP_PI_SSH_PASS" ssh $SSH_OPTS "$target" \
        "sudo mkdir -p /opt/oceanpulse/ops && sudo chown \$(whoami) /opt/oceanpulse/ops"

    # 2. Copy watchdog script
    echo "[2/5] Copying tailscale_watchdog.sh ..."
    sshpass -p "$OP_PI_SSH_PASS" scp $SSH_OPTS "$WATCHDOG_SCRIPT" "$target:/opt/oceanpulse/ops/tailscale_watchdog.sh"
    sshpass -p "$OP_PI_SSH_PASS" ssh $SSH_OPTS "$target" "chmod +x /opt/oceanpulse/ops/tailscale_watchdog.sh"

    # 3. Copy and install systemd units
    echo "[3/5] Installing systemd service + timer ..."
    sshpass -p "$OP_PI_SSH_PASS" scp $SSH_OPTS "$SERVICE_FILE" "$target:/tmp/tailscale-watchdog.service"
    sshpass -p "$OP_PI_SSH_PASS" scp $SSH_OPTS "$TIMER_FILE" "$target:/tmp/tailscale-watchdog.timer"
    sshpass -p "$OP_PI_SSH_PASS" ssh $SSH_OPTS "$target" \
        "sudo mv /tmp/tailscale-watchdog.service /etc/systemd/system/ && \
         sudo mv /tmp/tailscale-watchdog.timer /etc/systemd/system/ && \
         sudo systemctl daemon-reload"

    # 4. Enable timer (runs watchdog every 5 min + 30s after boot)
    echo "[4/5] Enabling tailscale-watchdog.timer ..."
    sshpass -p "$OP_PI_SSH_PASS" ssh $SSH_OPTS "$target" \
        "sudo systemctl enable --now tailscale-watchdog.timer"

    # 5. Run once immediately to verify
    echo "[5/5] Running watchdog now to verify ..."
    sshpass -p "$OP_PI_SSH_PASS" ssh $SSH_OPTS "$target" \
        "sudo systemctl start tailscale-watchdog.service && \
         echo 'Tailscale status:' && tailscale status --self 2>/dev/null && \
         echo 'Timer status:' && systemctl is-active tailscale-watchdog.timer"

    echo ""
    echo "OK: $name — Tailscale watchdog deployed and active."
    echo ""
}

# Parse target
TARGET="${1:-all}"

if [ "$TARGET" = "all" ]; then
    for sys in a b c d; do
        deploy_to "$sys" || echo "FAILED: ${SYSTEM_NAMES[$sys]} — skipping."
        echo ""
    done
else
    TARGET=$(echo "$TARGET" | tr '[:upper:]' '[:lower:]')
    if [[ ! -v "SYSTEMS[$TARGET]" ]]; then
        echo "Unknown system: $TARGET"
        echo "Usage: $0 [a|b|c|d|all]"
        exit 1
    fi
    deploy_to "$TARGET"
fi

echo "========================================"
echo "Deployment complete."
echo "Watchdog runs: 30s after boot + every 5 minutes."
echo "Logs: journalctl -t tailscale-watchdog"
echo "========================================"
