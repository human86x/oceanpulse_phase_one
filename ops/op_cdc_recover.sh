#!/bin/bash
# OceanPulse — Pi USB CDC-ACM dead-serial recovery.
#
# When the Pi-side cdc_acm driver enters the documented dead-serial state
# (Mega flashes OK, avrdude verifies, but Serial.print() yields 0 bytes),
# a full USB device unbind+bind on the parent USB port clears it.
# See memory/project_dead_serial_recovery_open.md (validated 2026-05-11/15).
#
# Usage: op_cdc_recover.sh <usb-device-id> [service-name]
#   usb-device-id   e.g. "3-1" (basename of /sys/class/tty/ttyACM0/device/..)
#   service-name    systemd unit to bounce (default: buoy-bridge-main.service)
#
# Must run as root. Bridge invokes via sudo (see /etc/sudoers.d/oceanpulse-cdc).

set -e
DEV_ID="${1:-3-1}"
SERVICE="${2:-buoy-bridge-main.service}"

if [ ! -d "/sys/bus/usb/devices/$DEV_ID" ]; then
    echo "[op_cdc_recover] ERROR: /sys/bus/usb/devices/$DEV_ID does not exist" >&2
    exit 2
fi

echo "[op_cdc_recover] $(date -Iseconds) recovering $DEV_ID (bouncing $SERVICE)"
systemctl stop "$SERVICE" || true
sleep 1
echo -n "$DEV_ID" > /sys/bus/usb/drivers/usb/unbind
sleep 2
echo -n "$DEV_ID" > /sys/bus/usb/drivers/usb/bind
sleep 3
systemctl start "$SERVICE" || true
echo "[op_cdc_recover] $(date -Iseconds) done"
