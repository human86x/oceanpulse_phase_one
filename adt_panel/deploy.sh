#!/bin/bash
# ADT Panel Deploy Script
# Used by Frontend_Engineer (UI) and Overseer (Data)
#
# Per ADT Framework:
# "Real-time, factual and shared transparency."

set -e

# Configuration
HOST="ftp.oceanpulse.pt"
USER="oceanpul"
PASS="sagres_2025Xx"
REMOTE_PATH="public_html/adt_panel"

# Local paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PANEL_DIR="$PROJECT_ROOT/adt_panel"
ADS_FILE="$PROJECT_ROOT/_cortex/ads/events.jsonl"
COMPILER_SCRIPT="$PROJECT_ROOT/_cortex/roles/Overseer/compile_ads.py"

echo "=== ADT Panel Deployment ==="
echo "Project: $PROJECT_ROOT"
echo "Panel: $PANEL_DIR"
echo "Target: $HOST/$REMOTE_PATH"

# Step 1: Refresh Data (Compile ADS)
if [ -f "$COMPILER_SCRIPT" ]; then
    echo ""
    echo "[1/3] Compiling latest ADS data..."
    python3 "$COMPILER_SCRIPT" "$ADS_FILE" "$PANEL_DIR/data.json"
else
    echo "Warning: Compiler script not found at $COMPILER_SCRIPT. Skipping data refresh."
fi

# Step 2: Upload to FTP
echo ""
echo "[2/3] Uploading to oceanpulse.pt..."

# Create remote directory if needed and upload files
lftp -u "$USER","$PASS" "$HOST" << EOF
set ssl:verify-certificate no
mkdir -p $REMOTE_PATH
cd $REMOTE_PATH
mput -O . $PANEL_DIR/index.html
mput -O . $PANEL_DIR/style.css
mput -O . $PANEL_DIR/panel.js
mput -O . $PANEL_DIR/data.json
mput -O . $PANEL_DIR/about.html
bye
EOF

# Step 3: Log to ADS
echo ""
echo "[3/3] Logging deployment to ADS..."

# Detect current user/agent context or default to generic
AGENT_NAME="${GEMINI_AGENT_NAME:-GEMINI}" 
# Fallback if variable not set
if [ "$AGENT_NAME" == "GEMINI" ]; then
    AGENT="GEMINI"
else
    AGENT="CLAUDE" # Assumed if not Gemini, usually manually set in real env
fi

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT_ID="evt_$(date +%Y%m%d_%H%M%S)_$(printf '%03d' $((RANDOM % 1000)))"

# We log it as a file_edit or adt_sync. adt_sync is better.
# Note: In a real shell session, the Agent/Role might need to be passed as args.
# For now, we'll ask the user to input role if running manually, or just log as "System" if automated.
# But since this is run by an Agent, the Agent should log the event manually via their standard procedure usually.
# However, the script itself can append to the log if it knows the role.

echo "Deployment complete."
echo "REMINDER: Please log this action to ADS manually if your agent environment requires it."
echo "URL: https://oceanpulse.pt/adt_panel/"
