#!/bin/bash
# Deploy and flash firmware to OceanPulse Pis

set -e

# System A (Main) - Directly accessible via WiFi
MAIN_HOST="192.168.43.37"
MAIN_USER="lab"
MAIN_PI="${MAIN_USER}@${MAIN_HOST}"

# System B (Health) - Directly accessible via WiFi
HEALTH_HOST="192.168.43.49"
HEALTH_USER="router"
HEALTH_PI="${HEALTH_USER}@${HEALTH_HOST}"

REMOTE_DIR="/tmp/oceanpulse_firmware"
BOARD="arduino:avr:mega"
PORT="/dev/ttyACM0"
PASS="777"
ARDUINO_CLI="/home/lab/arduino-cli"

# SSH Options
SSH_OPTS="-o StrictHostKeyChecking=no"

check_power() {
    local target=$1
    echo "=== Checking Power Status ($target) ==="
    if [ "$target" == "main" ]; then
        sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "vcgencmd get_throttled"
    else
        sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "vcgencmd get_throttled"
    fi
}

deploy_main() {
    echo "=== Deploying to MAIN Pi ($MAIN_HOST) ==="
    sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "mkdir -p $REMOTE_DIR"
    sshpass -p "$PASS" scp $SSH_OPTS -r firmware/main_mega $MAIN_PI:$REMOTE_DIR/
    sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "cd $REMOTE_DIR/main_mega && $ARDUINO_CLI compile -b $BOARD && $ARDUINO_CLI upload -b $BOARD -p $PORT"
    echo "=== Main firmware flashed ==="
}

deploy_health() {
    echo "=== Deploying to HEALTH Pi ($HEALTH_HOST) ==="
    sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "mkdir -p $REMOTE_DIR"
    sshpass -p "$PASS" scp $SSH_OPTS -r firmware/health_mega $HEALTH_PI:$REMOTE_DIR/
    
    # Check if arduino-cli is available, otherwise try local compile on Main Pi
    if sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "which arduino-cli > /dev/null"; then
        sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "cd $REMOTE_DIR/health_mega && arduino-cli compile -b $BOARD && arduino-cli upload -b $BOARD -p $PORT"
    else
        echo " -> arduino-cli not found on Health Pi. Attempting cross-compile on Main..."
        sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "mkdir -p /tmp/health_build"
        sshpass -p "$PASS" scp $SSH_OPTS -r firmware/health_mega $MAIN_PI:/tmp/health_build/
        sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "cd /tmp/health_build/health_mega && $ARDUINO_CLI compile -b $BOARD --output-dir /tmp/health_build/out"
        sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "sshpass -p '$PASS' scp $SSH_OPTS /tmp/health_build/out/health_mega.ino.hex ${HEALTH_PI}:$REMOTE_DIR/firmware.hex"
        sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "avrdude -v -p atmega2560 -c wiring -P $PORT -b 115200 -D -U flash:w:$REMOTE_DIR/firmware.hex:i"
    fi
    echo "=== Health firmware flashed ==="
}

test_main() {
    echo "=== Testing MAIN Arduino ==="
    sshpass -p "$PASS" ssh $SSH_OPTS $MAIN_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

test_health() {
    echo "=== Testing HEALTH Arduino ==="
    sshpass -p "$PASS" ssh $SSH_OPTS $HEALTH_PI "echo 'PING' | timeout 2 cat > $PORT; timeout 2 cat < $PORT"
}

case "$1" in
    main)   deploy_main ;;
    health) deploy_health ;;
    all)    deploy_main && deploy_health ;;
    test)   test_main && test_health ;;
    status) check_power main && check_power health ;;
    *)      echo "Usage: $0 {main|health|all|test|status}" ;;
esac