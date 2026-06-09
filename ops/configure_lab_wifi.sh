#!/bin/bash
# OceanPulse Lab Center Connectivity Configuration
# SPEC-022 Corrected
# Author: DevOps_Engineer (GEMINI)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS="$SCRIPT_DIR/secrets.env"
if [ ! -f "$SECRETS" ]; then
    echo "ERROR: $SECRETS not found. Copy ops/secrets.env.example and fill it in." >&2
    exit 1
fi
set -a; . "$SECRETS"; set +a

# Configuration
MAIN_SSID="${OP_LAB_WIFI_SSID:?OP_LAB_WIFI_SSID missing in secrets.env}"
MAIN_PASS="${OP_LAB_WIFI_PASS:?OP_LAB_WIFI_PASS missing in secrets.env}"
SUDO_PASS="${OP_SUDO_PASS:?OP_SUDO_PASS missing in secrets.env}"
MAIN_PRIORITY=100

echo "=== OceanPulse Lab Center WiFi Configuration (Corrected) ==="

# 1. Configure TP-Link_C7E2
echo "Configuring $MAIN_SSID..."
echo "$SUDO_PASS" | sudo -S nmcli connection delete "$MAIN_SSID" 2>/dev/null || true
echo "$SUDO_PASS" | sudo -S nmcli connection add type wifi con-name "$MAIN_SSID" ifname wlan0 ssid "$MAIN_SSID" -- wifi-sec.key-mgmt wpa-psk wifi-sec.psk "$MAIN_PASS" connection.autoconnect yes connection.autoconnect-priority "$MAIN_PRIORITY"

# 2. Clean up old non-existent networks
echo "Cleaning up non-existent networks..."
echo "$SUDO_PASS" | sudo -S nmcli connection delete "DIRECT-Ez-WP6" 2>/dev/null || true

# 3. Clean up proxy dispatcher
echo "Removing legacy proxy dispatcher..."
DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/99-proxy-DIRECT-Ez-WP6"
echo "$SUDO_PASS" | sudo -S rm -f $DISPATCHER_PATH
echo "$SUDO_PASS" | sudo -S rm -f /etc/profile.d/oceanpulse_proxy.sh

echo "=== Configuration Applied Successfully ==="
echo "To verify connection: nmcli connection show --active"
