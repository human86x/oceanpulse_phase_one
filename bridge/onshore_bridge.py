#!/usr/bin/env python3
import serial
import time
import requests
import json
import argparse
import sys
import re
import threading
from flask import Flask, request, jsonify

# Onshore Gateway Bridge: LoRa RX -> Web API & Web API -> LoRa TX
# Runs on System C (Onshore Gateway)

app = Flask(__name__)
bridge_instance = None

@app.route('/api/command', methods=['POST'])
def handle_command():
    if not bridge_instance:
        return jsonify({"status": "error", "message": "Bridge not initialized"}), 503

    data = request.json
    target_prefix = data.get("target") # 'M' or 'H'
    cmd = data.get("cmd")
    param = data.get("param")

    success = bridge_instance.send_command(target_prefix, cmd, param)
    if success:
        return jsonify({"status": "success", "message": f"Command {cmd} relayed to {target_prefix}"})
    else:
        return jsonify({"status": "error", "message": "Failed to relay command"}), 503

@app.route('/api/lora/test', methods=['POST'])
def handle_lora_test():
    if not bridge_instance or not bridge_instance.ser:
        return jsonify({"status": "error", "message": "Bridge not initialized"}), 503

    data = request.json
    mode = data.get("mode") if data else None

    if mode == "PING":
        t_start = time.time()
        success = bridge_instance.send_command("B", "PING")
        latency = round((time.time() - t_start) * 1000)
        if success:
            return jsonify({"status": "success", "message": "Ping sent via LoRa", "latency": latency, "pdr": 100})
        return jsonify({"status": "error", "message": "LoRa TX failed"}), 503

    if mode == "STRESS":
        success_count = 0
        for i in range(10):
            if bridge_instance.send_command("B", "STRESS", str(i)):
                success_count += 1
            time.sleep(0.3)
        pdr = round(success_count / 10 * 100)
        return jsonify({"status": "success", "message": f"Stress test complete. {success_count}/10 sent.", "pdr": pdr})

    return jsonify({"status": "error", "message": f"Unknown test mode: {mode}"}), 400


class OnshoreBridge:
    def __init__(self, port='/dev/ttyUSB0', baud=9600, api_url='http://localhost:5000/api/telemetry'):
        self.port = port
        self.baud = baud
        self.api_url = api_url
        self.ser = None
        self.running = False
        self.serial_lock = threading.Lock()
        self.tx_in_progress = False

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"Connected to LoRa-E5 on {self.port} at {self.baud} baud")
            # Initialize P2P Receive mode
            self._send_at_raw("AT+MODE=TEST")
            self._send_at_raw("AT+TEST=RFCFG,868,SF12,125,12,15,14,ON,OFF,OFF")
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False

    def _send_at_raw(self, cmd, wait=0.5):
        """Send AT command and read response. Caller must hold serial_lock or be in init."""
        if not self.ser: return ""
        self.ser.reset_input_buffer()
        self.ser.write(f"{cmd}\r\n".encode())
        time.sleep(wait)
        res = self.ser.read(self.ser.in_waiting or 1024).decode(errors='ignore')
        return res

    def listen_forever(self):
        print(f"Entering listen loop. Relaying to {self.api_url}")

        # Start Heartbeat thread
        def heartbeat():
            while self.running:
                try:
                    payload = {"target": "gateway", "data": {"online": True}}
                    requests.post(self.api_url, json=payload, timeout=5)
                except:
                    pass
                time.sleep(30)

        self.running = True
        h_thread = threading.Thread(target=heartbeat, daemon=True)
        h_thread.start()

        with self.serial_lock:
            self._send_at_raw("AT+TEST=RXLRPKT") # Start continuous RX

        try:
            while self.running:
                # Yield to TX operations
                if self.tx_in_progress:
                    time.sleep(0.1)
                    continue
                
                if self.ser.in_waiting == 0:
                    time.sleep(0.05)
                    continue

                line = self.ser.readline().decode(errors='ignore').strip()
                if line:
                    if "+TEST: RX" in line:
                        print(f"RAW RX: {line}")
                        match = re.search(r'RX "([0-9A-Fa-f]+)"', line)
                        if match:
                            hex_data = match.group(1)
                            try:
                                payload = bytes.fromhex(hex_data).decode(errors='ignore')
                                print(f"Decoded: {payload}")
                                self.process_payload(payload)
                            except Exception as e:
                                print(f"Decode error: {e}")
                    elif "RSSI:" in line:
                        print(f"Signal: {line}")
                        rssi_match = re.search(r'RSSI[:\s]*([-\d]+)', line)
                        snr_match = re.search(r'SNR[:\s]*([-\d]+)', line)
                        if rssi_match or snr_match:
                            signal_data = {"online": True, "lora_connected": True}
                            if rssi_match:
                                signal_data["rssi"] = int(rssi_match.group(1))
                            if snr_match:
                                signal_data["snr"] = int(snr_match.group(1))
                            try:
                                requests.post(self.api_url, json={"target": "gateway", "data": signal_data}, timeout=2)
                            except:
                                pass
        except Exception as e:
            print(f"Listen error: {e}")
        finally:
            if self.ser:
                self.ser.close()

    def process_payload(self, payload):
        # Format: M:TDS=515 or H:STATUS=RELAY=OFF,TEMP=25.0,HUM=50.0
        try:
            target_map = {"M": "main", "H": "health"}
            parts = payload.split(':')
            if len(parts) < 2: return

            prefix = parts[0]
            data_str = parts[1]

            target = target_map.get(prefix)
            if not target: return

            telemetry = {}
            if '=' in data_str:
                # Handle STATUS=k1=v1,k2=v2... or k=v
                if data_str.startswith("STATUS="):
                    status_content = data_str[7:] # Skip "STATUS="
                    kv_pairs = status_content.split(',')
                    for pair in kv_pairs:
                        if '=' in pair:
                            k, v = pair.split('=')
                            self._map_key_to_telemetry(k, v, telemetry)
                else:
                    k, v = data_str.split('=')
                    self._map_key_to_telemetry(k, v, telemetry)
            elif data_str == "ALIVE" or data_str == "PONG":
                telemetry["status"] = "online"

            if telemetry:
                self.push_to_api(target, telemetry)

        except Exception as e:
            print(f"Process error: {e}")

    def _map_key_to_telemetry(self, k, v, telemetry):
        """Helper to map LoRa keys to API telemetry fields."""
        v_clean = re.sub(r'[^0-9.A-Za-z]', '', v)

        if k == "TDS":
            try: telemetry["tds"] = float(v_clean)
            except: pass
        elif k == "TEMP":
            try: telemetry["temp"] = float(v_clean)
            except: pass
        elif k == "HUM":
            try: telemetry["hum"] = float(v_clean)
            except: pass
        elif k == "RELAY":
            telemetry["relay"] = v_clean
        elif k == "WD":
            telemetry["watchdog"] = v_clean
        elif k == "UPTIME":
            try: telemetry["uptime_ms"] = int(v_clean)
            except: pass

    def push_to_api(self, target, data):
        try:
            payload = {"target": target, "data": data}
            res = requests.post(self.api_url, json=payload, timeout=2)
            print(f"API Push {target}: {res.status_code}")
        except Exception as e:
            print(f"API Push error: {e}")

    def send_command(self, target_prefix, cmd, param=None):
        """Sends a downstream LoRa command: C:<TARGET>:<CMD>[:<PARAM>]

        Uses serial_lock + tx_in_progress flag to coordinate with listener thread.
        """
        if not self.ser: return False

        with self.serial_lock:
            self.tx_in_progress = True
            try:
                time.sleep(0.2)  # Let listener thread yield
                self.ser.reset_input_buffer()

                # Note: Do NOT re-send AT+MODE=TEST here.
                # It resets RFCFG to defaults, causing TX on wrong
                # radio parameters. Module is already in TEST mode
                # from connect().

                # Build and send packet
                packet = f"C:{target_prefix}:{cmd}"
                if param:
                    packet += f":{param}"

                hex_payload = packet.encode().hex()
                at_cmd = f'AT+TEST=TXLRPKT,"{hex_payload}"'
                print(f"Sending LoRa Command: {packet}")
                self.ser.reset_input_buffer()
                self.ser.write(f"{at_cmd}\r\n".encode())

                # Wait for TX DONE (SF12 can take 1-2s)
                time.sleep(2.5)
                res = self.ser.read(self.ser.in_waiting or 1024).decode(errors='ignore')
                print(f"TX Response: {repr(res)}")
                success = "TX DONE" in res

                # Resume RX mode
                self.ser.reset_input_buffer()
                self.ser.write(b"AT+TEST=RXLRPKT\r\n")
                time.sleep(0.3)
                self.ser.read(self.ser.in_waiting or 1024)  # drain

                return success
            except Exception as e:
                print(f"send_command error: {e}")
                return False
            finally:
                self.tx_in_progress = False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OceanPulse Onshore Gateway Bridge")
    parser.add_argument("--port", default='/dev/ttyUSB0', help="LoRa Serial Port")
    parser.add_argument("--api", default='http://localhost:5000/api/telemetry', help="Obs Center API URL")
    parser.add_argument("--web-port", type=int, default=5001, help="Port for Command API")
    args = parser.parse_args()

    bridge_instance = OnshoreBridge(port=args.port, api_url=args.api)
    if bridge_instance.connect():
        # Start listener thread
        listener_thread = threading.Thread(target=bridge_instance.listen_forever, daemon=True)
        listener_thread.start()

        # Start Flask API
        print(f"Starting Gateway Command API on port {args.web_port}")
        app.run(host='0.0.0.0', port=args.web_port)
