#!/bin/bash
# distribute_secrets.sh — push ops/secrets.env to every OceanPulse node
# and restart the services that consume it.
#
# Edit ops/secrets.env on the dev laptop (this machine), then run this script.
# It is the single source of truth; everywhere else is a synced copy.
#
# Usage:
#   ./ops/distribute_secrets.sh              # push to all nodes + restart services
#   ./ops/distribute_secrets.sh --dry-run    # show what would happen, do nothing
#
# Requires: sshpass (apt install sshpass), Tailscale up.
#
# Nodes:
#   Main Pi, Health Pi, Gateway — receive the file (future-proofing); no service
#     restart, since their bridges do not read OP_* env vars.
#   Lab Center, VPS              — receive the file AND restart obs-center.service,
#     which reads OP_FLASK_SECRET, OP_ADMIN_*, OP_FTP_*, OP_PI_SSH_PASS.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS="$SCRIPT_DIR/secrets.env"

if [ ! -f "$SECRETS" ]; then
    echo "ERROR: $SECRETS missing." >&2
    echo "Copy $SCRIPT_DIR/secrets.env.example to $SECRETS and fill it in." >&2
    exit 1
fi

set -a; . "$SECRETS"; set +a
: "${OP_PI_SSH_PASS:?OP_PI_SSH_PASS missing in secrets.env}"
: "${OP_SUDO_PASS:?OP_SUDO_PASS missing in secrets.env}"

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

# NAME | SSH TARGET | REMOTE PATH | SERVICE TO RESTART | AUTH (pwd|key)
NODES=(
    "Main Pi   |lab@100.115.88.91    |/home/lab/oceanpulse/ops/secrets.env    |                  |pwd"
    "Health Pi |router@100.116.100.92|/home/router/oceanpulse/ops/secrets.env |                  |pwd"
    "Gateway   |node1@100.64.151.40  |/home/node1/oceanpulse/ops/secrets.env  |                  |pwd"
    "Lab Center|lab@100.77.91.123    |/home/lab/oceanpulse/ops/secrets.env    |obs-center.service|pwd"
    "VPS       |ubuntu@57.129.121.36 |/home/ubuntu/oceanpulse/ops/secrets.env |obs-center.service|key"
)

# Quick TCP reachability test on port 22
ssh_reachable() {
    local host=${1#*@}
    timeout 3 bash -c "cat </dev/null >/dev/tcp/$host/22" 2>/dev/null
}

push_node() {
    local name="$1" target="$2" path="$3" svc="$4" auth="$5"

    echo "===================================================="
    echo "  $name  ($target)"
    echo "===================================================="

    if [ "$DRY_RUN" = "1" ]; then
        echo "  [dry-run] scp $SECRETS  →  $target:$path  (auth=$auth)"
        [ -n "$svc" ] && echo "  [dry-run] restart $svc"
        return 0
    fi

    if ! ssh_reachable "$target"; then
        echo "  SKIP: ${target#*@} unreachable on :22"
        return 1
    fi

    if [ "$auth" = "pwd" ]; then
        sshpass -p "$OP_PI_SSH_PASS" ssh -o StrictHostKeyChecking=no "$target" \
            "mkdir -p $(dirname "$path")"
        sshpass -p "$OP_PI_SSH_PASS" scp -o StrictHostKeyChecking=no "$SECRETS" "$target:$path"
        sshpass -p "$OP_PI_SSH_PASS" ssh -o StrictHostKeyChecking=no "$target" \
            "chmod 600 $path"
    else
        ssh -o StrictHostKeyChecking=no "$target" "mkdir -p $(dirname "$path")"
        scp -o StrictHostKeyChecking=no "$SECRETS" "$target:$path"
        ssh -o StrictHostKeyChecking=no "$target" "chmod 600 $path"
    fi
    echo "  OK: secrets.env synced (mode 600)"

    if [ -n "$svc" ]; then
        echo "  Restarting $svc ..."
        if [ "$auth" = "pwd" ]; then
            sshpass -p "$OP_PI_SSH_PASS" ssh -o StrictHostKeyChecking=no "$target" \
                "echo '$OP_SUDO_PASS' | sudo -S systemctl restart $svc && \
                 systemctl is-active $svc"
        else
            ssh -o StrictHostKeyChecking=no "$target" \
                "sudo systemctl restart $svc && systemctl is-active $svc"
        fi
        echo "  $svc restarted."
    fi
    return 0
}

failures=0
for row in "${NODES[@]}"; do
    IFS='|' read -r name target path svc auth <<< "$row"
    # Trim whitespace from each field
    name=$(echo "$name" | xargs)
    target=$(echo "$target" | xargs)
    path=$(echo "$path" | xargs)
    svc=$(echo "$svc" | xargs)
    auth=$(echo "$auth" | xargs)
    push_node "$name" "$target" "$path" "$svc" "$auth" || ((failures++))
    echo ""
done

echo "===================================================="
if [ "$failures" -gt 0 ]; then
    echo "  Complete with $failures failure(s)."
    exit 1
fi
echo "  All nodes synced. Live secrets are now consistent."
echo "===================================================="
