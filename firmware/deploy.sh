#!/bin/bash
# Deploy and flash firmware to OceanPulse Pis

set -e

MAIN_PI="lab@192.168.43.37"
HEALTH_PI="router@192.168.43.49"
REMOTE_DIR="/tmp/oceanpulse_firmware"
BOARD="arduino:avr:mega"
PORT="/dev/ttyACM0"
PASS="777"
ARDUINO_CLI="/home/lab/arduino-cli"

check_power() {
    local host=$1
    echo "=== Checking Power Status on $host ==="
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $host "vcgencmd get_throttled"
}

deploy_main() {
    echo "=== Deploying to MAIN Pi ==="
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $MAIN_PI "mkdir -p $REMOTE_DIR"
    sshpass -p "$PASS" scp -o StrictHostKeyChecking=no -r firmware/main_mega $MAIN_PI:$REMOTE_DIR/
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $MAIN_PI "cd $REMOTE_DIR/main_mega && $ARDUINO_CLI compile -b $BOARD && $ARDUINO_CLI upload -b $BOARD -p $PORT"
    echo "=== Main firmware flashed ==="
}

deploy_health() {
    echo "=== Deploying to HEALTH Pi ==="
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $HEALTH_PI "mkdir -p $REMOTE_DIR"
    sshpass -p "$PASS" scp -o StrictHostKeyChecking=no -r firmware/health_mega $HEALTH_PI:$REMOTE_DIR/
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $HEALTH_PI "cd $REMOTE_DIR/health_mega && $ARDUINO_CLI compile -b $BOARD && $ARDUINO_CLI upload -b $BOARD -p $PORT"
    echo "=== Health firmware flashed ==="
}

test_main() {
    echo "=== Testing MAIN Arduino ==="
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $MAIN_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

test_health() {
    echo "=== Testing HEALTH Arduino ==="
    sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $HEALTH_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

case "$1" in
    main)   deploy_main ;;
    health) deploy_health ;;
    all)    deploy_main && deploy_health ;;
    test)   test_main && test_health ;;
    status) check_power $MAIN_PI && check_power $HEALTH_PI ;;
    *)      echo "Usage: $0 {main|health|all|test|status}" ;;
esac