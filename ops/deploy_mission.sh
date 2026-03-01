#!/bin/bash
# OceanPulse Mission Deployment Script
# Usage: ./deploy_mission.sh [M|H|G]

CIRCUIT=$1
PORT_LORA="/dev/ttyUSB0"
PORT_MEGA="/dev/ttyACM0"

cd ~/oceanpulse/bridge

if [ "$CIRCUIT" == "M" ]; then
    echo "Starting Main Circuit Bridge..."
    nohup python3 buoy_bridge.py --circuit M --lora-port $PORT_LORA --mega-port $PORT_MEGA > ~/bridge.log 2>&1 &
elif [ "$CIRCUIT" == "H" ]; then
    echo "Starting Health Circuit Bridge..."
    nohup python3 buoy_bridge.py --circuit H --lora-port $PORT_LORA --mega-port $PORT_MEGA > ~/bridge.log 2>&1 &
elif [ "$CIRCUIT" == "G" ]; then
    echo "Starting Onshore Gateway..."
    API_URL="http://192.168.43.236:5000/api/telemetry"
    nohup python3 onshore_bridge.py --port $PORT_LORA --api $API_URL > ~/gateway.log 2>&1 &
else
    echo "Unknown circuit type: $CIRCUIT"
    exit 1
fi

sleep 2
ps aux | grep -E 'buoy_bridge.py|onshore_bridge.py' | grep -v grep
