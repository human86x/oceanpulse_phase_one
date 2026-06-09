#!/bin/bash
# OceanPulse: VPS Deployment Script
# Usage: ./deploy_vps.sh <vps_ip> <user>

VPS_IP=$1
USER=$2

if [ -z "$VPS_IP" ] || [ -z "$USER" ]; then
    echo "Usage: ./deploy_vps.sh <vps_ip> <user>"
    exit 1
fi

echo "=== Deploying Obs Center to VPS ($VPS_IP) ==="

# 1. Sync codebase
ssh -o StrictHostKeyChecking=accept-new $USER@$VPS_IP "mkdir -p ~/oceanpulse"
rsync -avz --progress -e "ssh -o StrictHostKeyChecking=accept-new" --exclude 'venv' --exclude '__pycache__' --exclude 'data/telemetry.db*' ./ $USER@$VPS_IP:~/oceanpulse/

# 2. Provision VPS (first time only ideally)
echo "Ensuring dependencies are installed on VPS..."
ssh -o StrictHostKeyChecking=accept-new $USER@$VPS_IP "sudo apt-get update && sudo apt-get install -y python3-pip python3-venv nginx rsync"

# 3. Setup Virtual Environment
echo "Setting up virtual environment..."
ssh -o StrictHostKeyChecking=accept-new $USER@$VPS_IP "cd ~/oceanpulse/obs_center && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"

# 4. Sync Database (Always sync for migration)
echo "Syncing database..."
rsync -avz --progress -e "ssh -o StrictHostKeyChecking=accept-new" obs_center/data/telemetry.db $USER@$VPS_IP:~/oceanpulse/obs_center/data/

# 5. Setup Systemd Service
echo "Configuring systemd service..."
ssh -o StrictHostKeyChecking=accept-new $USER@$VPS_IP "sudo cp ~/oceanpulse/ops/obs-center.service /etc/systemd/system/obs-center.service &&
    sudo sed -i \"s|/home/lab/|/home/$USER/|g\" /etc/systemd/system/obs-center.service &&
    sudo systemctl daemon-reload &&
    sudo systemctl enable obs-center.service &&
    sudo systemctl restart obs-center.service"

# 6. Setup Nginx
echo "Configuring Nginx..."
ssh -o StrictHostKeyChecking=accept-new $USER@$VPS_IP "sudo cp ~/oceanpulse/ops/nginx_obs_center.conf /etc/nginx/sites-available/obs_center &&
    sudo sed -i \"s|/home/lab/|/home/$USER/|g\" /etc/nginx/sites-available/obs_center &&
    sudo ln -sf /etc/nginx/sites-available/obs_center /etc/nginx/sites-enabled/ &&
    sudo rm -f /etc/nginx/sites-enabled/default &&
    sudo nginx -t &&
    sudo systemctl restart nginx"

echo "=== VPS Deployment Complete ==="
echo "Dashboard should be available at: http://$VPS_IP/"
