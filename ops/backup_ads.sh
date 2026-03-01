#!/bin/bash
# ADS Backup & Git Commit Script
# Part of the "Ledger Protocol" for Data Integrity

ADS_FILE="_cortex/ads/events.jsonl"
BACKUP_FILE="_cortex/ads/events.jsonl.bak"

# 1. Local File Rotation (Immediate Rollback)
if [ -f "$ADS_FILE" ]; then
    cp "$ADS_FILE" "$BACKUP_FILE"
    echo "✅ Local backup created: $BACKUP_FILE"
else
    echo "❌ Error: ADS file not found at $ADS_FILE"
    exit 1
fi

# 2. Git Commit (Permanent History)
# Check if there are changes to the ADS file
if git diff --quiet "$ADS_FILE"; then
    echo "ℹ️ No changes to ADS since last commit."
else
    git add "$ADS_FILE"
    TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
    git commit -m "ADS Auto-Backup: $TS"
    echo "✅ Changes committed to Git."
fi
