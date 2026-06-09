#!/bin/bash
# OceanPulse: Vision System Deployment
# Deploys to System A (Main Pi)

SYSTEM_A="100.115.88.91"
USER="lab"

echo "=== Deploying Vision Service to System A ($SYSTEM_A) ==="

# 1. Sync files
ssh $USER@$SYSTEM_A "mkdir -p ~/oceanpulse/vision"
rsync -avz --progress vision/ $USER@$SYSTEM_A:~/oceanpulse/vision/
rsync -avz --progress ops/vision.service $USER@$SYSTEM_A:~/oceanpulse/vision/

# 2. (Skipped: Using system packages)

# 3. Setup Systemd (requires sudo)
echo "Installing systemd service (requires sudo password on Pi)..."
ssh $USER@$SYSTEM_A "sudo cp ~/oceanpulse/vision/vision.service /etc/systemd/system/vision.service && 
    sudo systemctl daemon-reload && 
    sudo systemctl enable vision.service && 
    sudo systemctl restart vision.service"

echo "=== Deployment Complete ==="
echo "Status: http://$SYSTEM_A:5050/status"
echo "Stream: http://$SYSTEM_A:5050/stream"
