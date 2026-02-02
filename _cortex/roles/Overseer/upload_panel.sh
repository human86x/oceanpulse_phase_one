#!/bin/bash
# ADT Overseer: Upload Panel to oceanpulse.pt
#
# Per ADT Framework (Sheridan, 2026):
# "Real-time, factual and shared transparency."

set -e

# Configuration (from MEMORY_BANK)
HOST="ftp.oceanpulse.pt"
USER="oceanpul"
PASS="sagres_2025Xx"
REMOTE_PATH="public_html/adt_panel"

# Local paths
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../../.." && pwd)"
PANEL_DIR="$PROJECT_ROOT/adt_panel"
ADS_FILE="$PROJECT_ROOT/_cortex/ads/events.jsonl"

echo "=== ADT Oversight Panel Upload ==="
echo "Project: $PROJECT_ROOT"
echo "Panel: $PANEL_DIR"
echo "ADS: $ADS_FILE"
echo ""

# Step 1: Compile ADS to data.json
echo "[1/3] Compiling ADS events..."
python3 "$SCRIPT_DIR/compile_ads.py" "$ADS_FILE" "$PANEL_DIR/data.json"

# Step 2: Upload to FTP
echo ""
echo "[2/3] Uploading to $HOST..."

# Create remote directory if needed and upload files
lftp -u "$USER","$PASS" "$HOST" << EOF
set ssl:verify-certificate no
mkdir -p $REMOTE_PATH
cd $REMOTE_PATH
mput $PANEL_DIR/index.html
mput $PANEL_DIR/style.css
mput $PANEL_DIR/panel.js
mput $PANEL_DIR/data.json
bye
EOF

# Step 3: Log to ADS
echo ""
echo "[3/3] Logging sync event to ADS..."

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
EVENT_ID="evt_$(date +%Y%m%d_%H%M%S)_$(printf '%03d' $((RANDOM % 1000)))"

echo "{\"id\":\"$EVENT_ID\",\"ts\":\"$TIMESTAMP\",\"agent\":\"CLAUDE\",\"role\":\"Overseer\",\"action_type\":\"adt_sync\",\"spec_ref\":\"ADT-CONSTITUTION\",\"authority\":\"Article V Section 5.3\",\"authorized\":true,\"rationale\":\"Daily sync of oversight panel to oceanpulse.pt\",\"action_data\":{\"files_uploaded\":4,\"destination\":\"oceanpulse.pt/adt_panel/\"},\"outcome\":\"success\",\"escalation\":false}" >> "$ADS_FILE"

echo ""
echo "=== Upload Complete ==="
echo "Panel URL: https://oceanpulse.pt/adt_panel/"
