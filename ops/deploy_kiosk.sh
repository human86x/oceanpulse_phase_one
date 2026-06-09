#!/bin/bash
# OceanPulse Kiosk Deployment Script
# SPEC-021 Compliant

set -e

TARGET_PI="lab@192.168.43.236"
REMOTE_DIR="/home/lab/Projects/oceanpulse_phase_one"

echo "=== Deploying Headless Kiosk to Lab Center Pi ==="

# 1. Install Dependencies
echo "Installing dependencies (requires sudo)..."
ssh $TARGET_PI "sudo apt update && sudo apt install -y cage chromium-browser seatd"

# 2. Sync Files
echo "Uploading scripts and service files..."
scp ops/launch_kiosk.sh $TARGET_PI:$REMOTE_DIR/ops/
scp ops/obs-kiosk.service $TARGET_PI:/tmp/

# 3. Setup Systemd Service
echo "Enabling obs-kiosk service..."
ssh $TARGET_PI "sudo mv /tmp/obs-kiosk.service /etc/systemd/system/ && 
                sudo systemctl daemon-reload && 
                sudo systemctl enable obs-kiosk.service"

# 4. Seat Access
echo "Configuring seat access..."
ssh $TARGET_PI "sudo usermod -a -G render,video,seat lab"

echo "=== Deployment Complete ==="
echo "To start the kiosk now: ssh $TARGET_PI 'sudo systemctl start obs-kiosk'"
