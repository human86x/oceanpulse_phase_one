#!/bin/bash
# OceanPulse: Obs Center Deployment
# Deploys to System D (Lab Center)

SYSTEM_D="100.77.91.123"
USER="lab"

echo "=== Deploying Obs Center to System D ($SYSTEM_D) ==="

# 1. Sync files
ssh $USER@$SYSTEM_D "mkdir -p ~/oceanpulse/obs_center"
rsync -avz --progress obs_center/ $USER@$SYSTEM_D:~/oceanpulse/obs_center/

# 2. Setup Systemd (requires sudo)
echo "Installing systemd service (requires sudo password on Pi)..."
ssh $USER@$SYSTEM_D "sudo cp ~/oceanpulse/obs_center/obs-center.service /etc/systemd/system/obs-center.service &&
    sudo systemctl daemon-reload &&
    sudo systemctl enable obs-center.service &&
    sudo systemctl restart obs-center.service"

echo "=== Deployment Complete ==="
echo "Dashboard: http://$SYSTEM_D:5000/"
echo "API: http://$SYSTEM_D:5000/api/telemetry"
