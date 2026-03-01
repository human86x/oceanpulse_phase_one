import os
import sys
import time
import logging
from flask import Flask, render_template, jsonify, request

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OpsCenter")

# Ensure we can import from bridge directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bridge.main_bridge import MainBridge
from bridge.health_bridge import HealthBridge
from bridge.lora_handler import LoraHandler

# Optional: paramiko/requests for remote SSH and Gateway API
try:
    import paramiko
    HAS_PARAMIKO = True
except ImportError:
    HAS_PARAMIKO = False
    logger.warning("paramiko not installed. Remote SSH commands disabled.")

try:
    import requests as http_requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logger.warning("requests not installed. Gateway API routing disabled.")

app = Flask(__name__)

# System Configurations (Tailscale IPs from MEMORY_BANK.md)
SYSTEMS = {
    "main": {
        "host": "100.115.88.91",
        "user": "lab",
        "pass": "777",
        "bridge_path": "~/oceanpulse/bridge/main_bridge.py",
        "port": "/dev/ttyACM0"
    },
    "health": {
        "host": "100.116.100.92",
        "user": "router",
        "pass": "777",
        "bridge_path": "~/oceanpulse/bridge/health_bridge.py",
        "port": "/dev/ttyACM0"
    },
    "gateway": {
        "host": "100.64.151.40",
        "port": 5001,
        "api_url": "http://100.64.151.40:5001/api/command"
    },
    "lab-center": {
        "host": "100.77.91.123",
        "user": "lab",
        "pass": "777"
    }
}

# --- Safe Hardware Initialization ---
# Only connect to local hardware if ports actually exist.
# On lab-center (no Arduinos) or dev laptop, these stay None.
main_bridge = None
health_bridge = None
lora_handler = None

MAIN_PORT = os.environ.get("OP_MAIN_PORT", "/dev/ttyACM0")
HEALTH_PORT = os.environ.get("OP_HEALTH_PORT", "/dev/ttyACM1")
LORA_PORT = os.environ.get("OP_LORA_PORT", "/dev/ttyUSB0")

def init_local_hardware():
    """Try to connect to local serial devices. Failures are non-fatal."""
    global main_bridge, health_bridge, lora_handler

    if os.path.exists(MAIN_PORT):
        try:
            main_bridge = MainBridge(port=MAIN_PORT)
            if main_bridge.connect():
                logger.info(f"Main bridge connected on {MAIN_PORT}")
            else:
                main_bridge = None
        except Exception as e:
            logger.warning(f"Main bridge init failed: {e}")
            main_bridge = None
    else:
        logger.info(f"Main port {MAIN_PORT} not found - running without local Main bridge")

    if os.path.exists(HEALTH_PORT):
        try:
            health_bridge = HealthBridge(port=HEALTH_PORT)
            if health_bridge.connect():
                logger.info(f"Health bridge connected on {HEALTH_PORT}")
            else:
                health_bridge = None
        except Exception as e:
            logger.warning(f"Health bridge init failed: {e}")
            health_bridge = None
    else:
        logger.info(f"Health port {HEALTH_PORT} not found - running without local Health bridge")

    if os.path.exists(LORA_PORT):
        try:
            lora_handler = LoraHandler(port=LORA_PORT, baud=9600, mode='AT')
            if lora_handler.connect():
                logger.info(f"LoRa connected on {LORA_PORT}")
            else:
                lora_handler = None
        except Exception as e:
            logger.warning(f"LoRa init failed: {e}")
            lora_handler = None
    else:
        logger.info(f"LoRa port {LORA_PORT} not found - running without local LoRa")

# System state — always available regardless of hardware
system_state = {
    "main": {
        "online": False,
        "tds": 0,
        "ph": 7.0,
        "water_temp": 0.0,
        "voltage": 0.0,
        "relay": "OFF",
        "last_update": 0
    },
    "health": {
        "online": False,
        "temp": 0.0,
        "hum": 0.0,
        "uptime": "N/A",
        "last_update": 0
    },
    "gateway": {
        "online": False,
        "last_update": 0
    },
    "lora": {
        "connected": False,
        "last_rssi": 0,
        "last_snr": 0,
        "mode": "AT",
        "preset": "LONG_SLOW",
        "freq": 868.0,
        "sf": "SF12",
        "packets_sent": 0,
        "packets_received": 0
    }
}


def execute_remote_command(target, command):
    """Executes a bridge command on a remote Pi via SSH."""
    if not HAS_PARAMIKO:
        return {"status": "error", "message": "SSH disabled (paramiko not installed)"}

    config = SYSTEMS.get(target)
    if not config or "bridge_path" not in config:
        return {"status": "error", "message": f"No SSH config for target '{target}'"}

    try:
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(config["host"], username=config["user"], password=config["pass"], timeout=5)

        cmd_str = f"python3 {config['bridge_path']} --port {config['port']} --command {command}"
        stdin, stdout, stderr = ssh.exec_command(cmd_str)

        output = stdout.read().decode().strip()
        error = stderr.read().decode().strip()
        ssh.close()

        if error and not output:
            return {"status": "error", "message": error}

        try:
            import json
            return json.loads(output)
        except (ValueError, TypeError):
            return {"status": "success", "raw": output}

    except Exception as e:
        return {"status": "error", "message": f"SSH failed: {str(e)}"}


def update_telemetry():
    """Check hardware staleness. Telemetry is pushed via POST /api/telemetry."""
    # Mark systems offline if no update received in 30s
    now = time.time()
    for key in ("main", "health", "gateway"):
        if now - system_state[key]["last_update"] > 30:
            system_state[key]["online"] = False

    # Update local LoRa status (only if we have a local handler)
    if lora_handler:
        system_state["lora"]["connected"] = lora_handler.connected
    else:
        system_state["lora"]["connected"] = False


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/telemetry', methods=['GET', 'POST'])
def handle_telemetry():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON body"}), 400

        target = data.get("target")
        payload = data.get("data", {})

        if target not in system_state:
            return jsonify({"status": "error", "message": f"Unknown target '{target}'"}), 400

        # Update specific fields (only known keys)
        for key, value in payload.items():
            if key in system_state[target]:
                system_state[target][key] = value

        # Gateway can also report LoRa link status
        if target == "gateway":
            if "lora_connected" in payload:
                system_state["lora"]["connected"] = payload["lora_connected"]
            if "rssi" in payload:
                system_state["lora"]["last_rssi"] = payload["rssi"]
            if "snr" in payload:
                system_state["lora"]["last_snr"] = payload["snr"]

        system_state[target]["online"] = True
        system_state[target]["last_update"] = time.time()
        return jsonify({"status": "success", "message": f"Telemetry updated for {target}"})

    # GET — return current state
    update_telemetry()
    return jsonify(system_state)


@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    target = data.get("target")
    cmd = data.get("cmd")

    if not target or not cmd:
        return jsonify({"status": "error", "message": "Missing 'target' or 'cmd'"}), 400

    if cmd not in ("REBOOT", "RELAY_ON", "RELAY_OFF"):
        return jsonify({"status": "error", "message": f"Unsupported command: {cmd}"}), 400

    # Step 1: Try Gateway API (LoRa mission protocol)
    if HAS_REQUESTS:
        target_prefix = "M" if target == "main" else "H"
        lora_cmd = "REBOOT" if cmd == "REBOOT" else "RELAY"
        lora_param = None if cmd == "REBOOT" else ("ON" if cmd == "RELAY_ON" else "OFF")

        try:
            gateway_url = SYSTEMS["gateway"]["api_url"]
            payload = {"target": target_prefix, "cmd": lora_cmd, "param": lora_param}
            res = http_requests.post(gateway_url, json=payload, timeout=5)
            if res.status_code == 200:
                return jsonify({"status": "success", "message": f"Command {cmd} relayed via Gateway to {target}"})
            else:
                logger.warning(f"Gateway returned {res.status_code}: {res.text}")
        except Exception as e:
            logger.warning(f"Gateway unreachable: {e}")

    # Step 2: Fallback to SSH for RELAY commands
    if cmd != "REBOOT" and target in ("main", "health"):
        bridge_cmd = "ON" if cmd == "RELAY_ON" else "OFF"
        result = execute_remote_command(target, bridge_cmd)
        return jsonify(result)

    # Step 3: REBOOT via SSH fallback
    if cmd == "REBOOT" and target in ("main", "health"):
        result = execute_remote_command(target, "REBOOT")
        return jsonify(result)

    return jsonify({"status": "error", "message": f"Command {cmd} for {target} failed (Gateway + SSH both unreachable)"}), 503


@app.route('/api/lora/config', methods=['POST'])
def lora_config():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    preset = data.get("preset")
    if not preset:
        return jsonify({"status": "error", "message": "Missing 'preset'"}), 400

    system_state["lora"]["preset"] = preset

    if preset == "CUSTOM":
        if "freq" in data:
            system_state["lora"]["freq"] = float(data["freq"])
        if "sf" in data:
            system_state["lora"]["sf"] = data["sf"]
        return jsonify({"status": "success", "message": f"Custom LoRa: {system_state['lora']['freq']}MHz, {system_state['lora']['sf']}"})

    return jsonify({"status": "success", "message": f"LoRa preset set to {preset}"})


@app.route('/api/lora/test', methods=['POST'])
def lora_test():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    mode = data.get("mode")

    # Route 1: Proxy to Gateway (System C) — it has the LoRa hardware
    if HAS_REQUESTS:
        try:
            gateway_test_url = f"http://{SYSTEMS['gateway']['host']}:{SYSTEMS['gateway']['port']}/api/lora/test"
            res = http_requests.post(gateway_test_url, json={"mode": mode}, timeout=15)
            result = res.json()
            if result.get("status") == "success":
                system_state["lora"]["packets_sent"] += 1
            return jsonify(result), res.status_code
        except Exception as e:
            logger.warning(f"Gateway LoRa test proxy failed: {e}")

    # Route 2: Local LoRa hardware (if available on this node)
    if lora_handler and lora_handler.connected:
        if mode == "PING":
            success = lora_handler.send_text("M:PING")
            if success:
                system_state["lora"]["packets_sent"] += 1
                return jsonify({"status": "success", "message": "Ping sent via LoRa"})
            return jsonify({"status": "error", "message": "LoRa send failed"}), 503

        if mode == "STRESS":
            success_count = 0
            for i in range(10):
                if lora_handler.send_text(f"M:STRESS={i}"):
                    success_count += 1
                    system_state["lora"]["packets_sent"] += 1
                time.sleep(0.2)
            return jsonify({"status": "success", "message": f"Stress test complete. {success_count}/10 sent."})

    return jsonify({"status": "error", "message": "LoRa test failed: Gateway unreachable and no local LoRa hardware"}), 503


# --- Startup ---

init_local_hardware()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
