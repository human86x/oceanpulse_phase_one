#!/bin/bash
# OceanPulse Lab Center Connectivity Configuration
# SPEC-022 Compliant
# Author: DevOps_Engineer (GEMINI)

set -e

# Configuration
DIRECT_SSID="DIRECT-Ez-WP6"
DIRECT_PASS="vYiLs9sL"
DIRECT_PRIORITY=100
DIRECT_PROXY="http://192.168.49.1:8228"

MARTINHAL_SSID_PREFIX="Martinhal"
MARTINHAL_PRIORITY=0

echo "=== OceanPulse Lab Center WiFi Configuration ==="

# 1. Configure DIRECT-Ez-WP6
echo "Configuring $DIRECT_SSID..."
nmcli connection delete "$DIRECT_SSID" 2>/dev/null || true
nmcli connection add 
    type wifi 
    con-name "$DIRECT_SSID" 
    ifname wlan0 
    ssid "$DIRECT_SSID" 
    -- 
    wifi-sec.key-mgmt wpa-psk 
    wifi-sec.psk "$DIRECT_PASS" 
    connection.autoconnect yes 
    connection.autoconnect-priority "$DIRECT_PRIORITY"

# 2. Configure Martinhal (Open)
# Note: Since the exact SSID suffix might vary, we look for available ones
echo "Looking for Martinhal networks..."
SCAN_SSID=$(nmcli dev wifi list | grep "$MARTINHAL_SSID_PREFIX" | head -n 1 | awk '{print $2}')

if [ -z "$SCAN_SSID" ]; then
    SCAN_SSID="$MARTINHAL_SSID_PREFIX"
    echo "Warning: Martinhal network not visible in scan, using default name: $SCAN_SSID"
else
    echo "Found Martinhal SSID: $SCAN_SSID"
fi

nmcli connection delete "$SCAN_SSID" 2>/dev/null || true
nmcli connection add 
    type wifi 
    con-name "$SCAN_SSID" 
    ifname wlan0 
    ssid "$SCAN_SSID" 
    -- 
    connection.autoconnect yes 
    connection.autoconnect-priority "$MARTINHAL_PRIORITY"

# 3. Proxy Configuration for DIRECT-Ez-WP6
# We use a NetworkManager dispatcher script to set/unset proxy globally
echo "Setting up network-specific proxy dispatcher..."

DISPATCHER_PATH="/etc/NetworkManager/dispatcher.d/99-proxy-DIRECT-Ez-WP6"

cat <<EOF > /tmp/99-proxy
#!/bin/bash
# Dispatcher script for SPEC-022 Proxy enforcement

INTERFACE=\$1
ACTION=\$2

# Get SSID of the connecting/disconnecting network
CONNECTION_SSID=\$(nmcli -t -f name connection show --active | grep "$DIRECT_SSID")

if [ "\$CONNECTION_SSID" == "$DIRECT_SSID" ]; then
    case "\$ACTION" in
        up)
            echo "DIRECT-Ez-WP6 detected. Setting proxy..."
            # For system-wide environment (requires reboot or sourcing)
            echo "export http_proxy="$DIRECT_PROXY"" > /etc/profile.d/oceanpulse_proxy.sh
            echo "export https_proxy="$DIRECT_PROXY"" >> /etc/profile.d/oceanpulse_proxy.sh
            echo "export no_proxy="localhost,127.0.0.1,192.168.43.0/24"" >> /etc/profile.d/oceanpulse_proxy.sh
            ;;
        down)
            echo "DIRECT-Ez-WP6 disconnected. Removing proxy..."
            rm -f /etc/profile.d/oceanpulse_proxy.sh
            ;;
    esac
fi
EOF

sudo mv /tmp/99-proxy $DISPATCHER_PATH
sudo chmod +x $DISPATCHER_PATH

echo "=== Configuration Applied Successfully ==="
echo "Note: Proxy settings in /etc/profile.d/ will take effect for NEW shells."
echo "To verify connection: nmcli connection show --active"
