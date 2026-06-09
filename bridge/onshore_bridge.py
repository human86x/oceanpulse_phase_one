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
    def __init__(self, port='/dev/op-lora', baud=9600, api_url='http://localhost:5000/api/telemetry', public_api=None):
        self.port = port
        self.baud = baud
        self.api_urls = [api_url]
        if public_api:
            self.api_urls.append(public_api)
        self.ser = None
        self.running = False
        self.serial_lock = threading.Lock()
        self.tx_in_progress = False
        self.shell_chunks = {} # cmd_id -> [chunks]

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=1)
            print(f"Connected to LoRa-E5 on {self.port} at {self.baud} baud")
            
            # Reset module state if busy
            for attempt in range(5):
                res = self._send_at_raw("AT")
                if "OK" in res: break
                print(f"Module busy or not responding (attempt {attempt+1})...")
                time.sleep(1)

            # Initialize P2P mode
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
        print(f"Entering listen loop. Relaying to {self.api_urls}")

        # Start Heartbeat thread
        def heartbeat():
            while self.running:
                try:
                    payload = {"target": "gateway", "data": {"online": True}}
                    self.push_payload(payload)
                except:
                    pass
                time.sleep(30)

        self.running = True
        h_thread = threading.Thread(target=heartbeat, daemon=True)
        h_thread.start()

        with self.serial_lock:
            for attempt in range(3):
                res = self._send_at_raw("AT+TEST=RXLRPKT") # Start continuous RX
                if "RXLRPKT" in res or "OK" in res: break
                print(f"Failed to enter RX mode (attempt {attempt+1}): {repr(res)}")
                time.sleep(1)

        try:
            buffer = ""
            while self.running:
                # Yield to TX operations
                if self.tx_in_progress:
                    time.sleep(0.1)
                    continue
                
                if self.ser.in_waiting > 0:
                    chunk = self.ser.read(self.ser.in_waiting).decode(errors='ignore')
                    buffer += chunk
                    
                    if "\n" in buffer or "\r" in buffer:
                        # Split by both \n and \r
                        lines = re.split(r'[\r\n]+', buffer)
                        # Keep the last partial line in the buffer
                        buffer = lines.pop() if not buffer.endswith(("\n", "\r")) else ""
                        
                        for line in lines:
                            line = line.strip()
                            if not line: continue
                            
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
                                    self.push_payload({"target": "gateway", "data": signal_data})
                else:
                    time.sleep(0.1)
        except Exception as e:
            print(f"Listen error: {e}")
        finally:
            if self.ser:
                self.ser.close()

    def process_payload(self, payload):
        # Format: M:TDS=515 or H:STATUS=RELAY=OFF,TEMP=25.0,HUM=50.0
        try:
            target_map = {"M": "main", "H": "health", "P": "power"}
            parts = payload.split(':')
            if len(parts) < 2: return

            prefix = parts[0]
            data_str = parts[1]

            target = target_map.get(prefix)
            if not target: return

            # SPEC-036: Power packets get their own routing — compact keys
            # expand into a structured {mppt, shunt} dict; obs_center handles
            # derived fields server-side.
            if prefix == "P" and data_str.startswith("STATUS="):
                power = self._parse_power_payload(data_str[7:])
                if power:
                    self.push_to_api("power", power)
                return

            telemetry = {}
            if '=' in data_str:
                # Handle STATUS=k1=v1,k2=v2... or k=v
                if data_str.startswith("STATUS="):
                    status_content = data_str[7:] # Skip "STATUS="
                    kv_pairs = status_content.split(',')
                    
                    for pair in kv_pairs:
                        if '=' not in pair: continue
                        k, v = pair.split('=', 1)
                        self._map_key_to_telemetry(k, v, telemetry)
                else:
                    k, v = data_str.split('=', 1)
                    self._map_key_to_telemetry(k, v, telemetry)
            elif data_str == "ALIVE" or data_str == "PONG":
                telemetry["status"] = "online"

            # Handle SOFT_REBOOT ACK
            if len(parts) >= 3 and parts[1] == "SOFT_REBOOT" and parts[2] == "ACK":
                print(f"SOFT_REBOOT ACK received from {target}")
                self.push_to_api(target, {"soft_reboot_ack": True, "status": "rebooting"})
                return

            if telemetry:
                self.push_to_api(target, telemetry)

            # Handle SHELL ACK (SPEC-026 chunked)
            # Format: <TARGET>:SHELL:ACK:<CMD_ID>:<CHUNK_IDX>:<TOTAL_CHUNKS>:<BASE64_DATA>
            if len(parts) >= 7 and parts[1] == "SHELL" and parts[2] == "ACK":
                import base64
                cmd_id = parts[3]
                try:
                    idx = int(parts[4])
                    total = int(parts[5])
                    b64_data = parts[6]
                    
                    if cmd_id not in self.shell_chunks:
                        self.shell_chunks[cmd_id] = [None] * total
                    
                    self.shell_chunks[cmd_id][idx] = b64_data
                    
                    # Check if all chunks arrived
                    if all(c is not None for c in self.shell_chunks[cmd_id]):
                        full_b64 = "".join(self.shell_chunks[cmd_id])
                        full_output = base64.b64decode(full_b64).decode('utf-8', errors='replace')
                        print(f"SHELL Complete (ID: {cmd_id}): {full_output}")
                        self.push_to_api(target, {
                            "shell_ack": True, 
                            "cmd_id": cmd_id, 
                            "output": full_output,
                            "status": "complete"
                        })
                        del self.shell_chunks[cmd_id]
                except Exception as e:
                    print(f"Shell ACK processing error: {e}")
                return

        except Exception as e:
            print(f"Process error: {e}")

    # SPEC-036 — Power packet field decoders. Each entry maps a compact key
    # to (subsystem, field_name, scaler). Scaler turns the wire integer back
    # into a real float/int with units (V, A, W, %).
    POWER_KEY_MAP = {
        "PV":  ("mppt",  "panel_v",  lambda v: float(v) / 10),    # decivolts -> V
        "PW":  ("mppt",  "panel_w",  int),                         # W
        "CI":  ("mppt",  "charge_i", lambda v: float(v) / 100),   # centi-A -> A
        "LI":  ("mppt",  "load_i",   lambda v: float(v) / 100),
        "CS":  ("mppt",  "cs",       int),
        "ER":  ("mppt",  "err",      int),
        "SV":  ("shunt", "batt_v",   lambda v: float(v) / 100),   # centivolts -> V
        "SI":  ("shunt", "batt_i",   lambda v: float(v) / 100),
        "SP":  ("shunt", "batt_p",   int),                         # W (signed)
        "SOC": ("shunt", "soc",      lambda v: float(v) / 10),    # tenths-% -> %
    }

    def _parse_power_payload(self, body):
        """Parse 'PV=196,PW=25,CI=54,...' into nested {mppt:{...}, shunt:{...}}.
        Unknown keys are ignored; malformed values are silently dropped."""
        power = {"mppt": {}, "shunt": {}}
        for pair in body.split(","):
            if "=" not in pair:
                continue
            k, _, v = pair.partition("=")
            k = k.strip()
            v = v.strip()
            entry = self.POWER_KEY_MAP.get(k)
            if not entry:
                continue
            subsys, field, scaler = entry
            try:
                power[subsys][field] = scaler(v)
            except (TypeError, ValueError):
                continue
        if not power["mppt"] and not power["shunt"]:
            return None
        return power

    # Short aliases emitted by buoy_bridge to fit Health under the SF12 packet
    # ceiling. Expanded back to long keys before the existing routing.
    SHORT_KEY_ALIASES = {
        "ST": "SHT_T",   "SH": "SHT_H",
        "T1": "DHT1_T",  "H1": "DHT1_H",
        "T2": "DHT2_T",  "H2": "DHT2_H",
        "T3": "DHT3_T",  "H3": "DHT3_H",
        "T4": "DHT4_T",  "H4": "DHT4_H",
        "B":  "BATT",
    }

    def _map_key_to_telemetry(self, k, v, telemetry):
        """Helper to map LoRa keys to API telemetry fields."""
        v_clean = re.sub(r'[^0-9.A-Za-z]', '', v)
        # Numeric-only view of v with unit suffixes stripped (V, °C, %, ppm, mg, etc.)
        v_num = re.sub(r'[^0-9.\-]', '', v)
        k_upper = k.upper()
        k_upper = self.SHORT_KEY_ALIASES.get(k_upper, k_upper)

        if k_upper == "EC":
            try: telemetry["ec"] = float(v_num)
            except: telemetry["ec"] = v_clean
        elif k_upper == "DO":
            try: telemetry["do"] = float(v_num)
            except: telemetry["do"] = v_clean
        elif k_upper == "SAT":
            # DO saturation % — obs_center computes mg/L from this + temp + salinity
            try: telemetry["do_sat"] = float(v_num)
            except: pass
        elif k_upper == "SAL":
            # Salinity (PSU/PPT) — from Atlas EZO-EC when firmware exposes it
            try: telemetry["salinity"] = float(v_num)
            except: pass
        elif k_upper in ("WTEMP", "WATER_TEMP"):
            try: telemetry["water_temp"] = float(v_num)
            except: pass
        elif k_upper == "TEMP":
            # Health-circuit SHT3x temperature (kept legacy name for compat)
            try: telemetry["temp"] = float(v_num)
            except: pass
        elif k_upper == "HUM":
            try: telemetry["hum"] = float(v_num)
            except: pass
        elif k_upper == "BATT":
            try: telemetry["voltage"] = float(v_num)
            except: pass
        elif k_upper == "DIST":
            try: telemetry["distance"] = float(v_num)
            except: telemetry["distance"] = v_clean
        elif k_upper == "RELAY":
            telemetry["relay"] = v_clean
        elif k_upper == "WD":
            telemetry["watchdog"] = v_clean
        elif k_upper == "UPTIME":
            try: telemetry["uptime_ms"] = int(v_clean)
            except: pass
        elif k_upper == "BRAKE":
            telemetry["brake"] = v_clean
        # DHT11 sensors emitted as DHT[1-4]_T / DHT[1-4]_H (DHT4 added 2026-05-30)
        elif k_upper in ("DHT1_T", "DHT2_T", "DHT3_T", "DHT4_T"):
            try: telemetry[k_upper.lower().replace("_t", "_temp")] = float(v_num)
            except: pass
            # never falls through
        elif k_upper in ("DHT1_H", "DHT2_H", "DHT3_H", "DHT4_H"):
            try: telemetry[k_upper.lower().replace("_h", "_hum")] = float(v_num)
            except: pass
        # SHT3x reference sensor — synthesized from `SHT=T=X,H=Y` nested format
        elif k_upper == "SHT_T":
            try: telemetry["temp"] = float(v_num)
            except: pass
        elif k_upper == "SHT_H":
            try: telemetry["hum"] = float(v_num)
            except: pass

    def push_to_api(self, target, data):
        payload = {"target": target, "data": data}
        self.push_payload(payload)

    def push_payload(self, payload):
        headers = {'User-Agent': 'OceanPulse-Bridge/1.0'}
        for url in self.api_urls:
            try:
                res = requests.post(url, json=payload, headers=headers, timeout=2)
                print(f"API Push {url} ({payload.get('target')}): {res.status_code}")
            except Exception as e:
                print(f"API Push error {url}: {e}")

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
                time.sleep(3.5)
                res = self.ser.read(self.ser.in_waiting or 1024).decode(errors='ignore')
                print(f"TX Response: {repr(res)}")
                # Success if TX DONE OR if TXLRPKT/LORA TX appeared in verbose logs (REQ-029)
                success = any(x in res for x in ["TX DONE", "TXLRPKT", "LORA    TX"])

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

@app.route('/api/wifi/status', methods=['GET'])
def get_wifi_status():
    """Return status of wlan0 and wlan1."""
    try:
        def get_iface_status(iface):
            # Check if UP/DOWN via ip link
            ip_out = subprocess.check_output(["ip", "link", "show", iface], stderr=subprocess.STDOUT).decode()
            is_up = "state UP" in ip_out
            
            # Check connection name via nmcli
            try:
                nm_out = subprocess.check_output(["nmcli", "-t", "-f", "DEVICE,CONNECTION", "device"], stderr=subprocess.STDOUT).decode()
                conn = "Disconnected"
                for line in nm_out.splitlines():
                    if line.startswith(f"{iface}:"):
                        conn = line.split(":")[1] or "Disconnected"
                        break
            except:
                conn = "Unknown"
            
            # Check IP
            try:
                addr_out = subprocess.check_output(["ip", "-4", "addr", "show", iface], stderr=subprocess.STDOUT).decode()
                ip_match = re.search(r'inet\s+([\d\.]+)', addr_out)
                ip_addr = ip_match.group(1) if ip_match else "No IP"
            except:
                ip_addr = "N/A"
                
            return {"up": is_up, "connection": conn, "ip": ip_addr}

        status = {
            "wlan0": get_iface_status("wlan0"),
            "wlan1": get_iface_status("wlan1")
        }
        return jsonify({"status": "success", "interfaces": status})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/wifi/control', methods=['POST'])
def control_wifi():
    """Enable/Disable WiFi interfaces or connections."""
    data = request.json
    if not data or 'interface' not in data or 'action' not in data:
        return jsonify({"status": "error", "message": "Missing params"}), 400
    
    iface = data['interface']
    action = data['action'] # "UP", "DOWN"
    
    if iface not in ["wlan0", "wlan1"]:
        return jsonify({"status": "error", "message": "Invalid interface"}), 400
        
    try:
        # We use nmcli if possible as it handles connections better
        if action == "UP":
            # Find the best connection for this interface
            subprocess.check_call(["sudo", "nmcli", "device", "set", iface, "managed", "yes"])
            # Try to up the specifically configured connection if known
            if iface == "wlan1":
                subprocess.check_call(["sudo", "nmcli", "connection", "up", "Buoy-LongRange"])
            else:
                subprocess.check_call(["sudo", "nmcli", "device", "connect", iface])
        else:
            subprocess.check_call(["sudo", "nmcli", "device", "disconnect", iface])
            
        return jsonify({"status": "success", "message": f"Interface {iface} set to {action}"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="OceanPulse Onshore Gateway Bridge")
    parser.add_argument("--port", default='/dev/op-lora', help="LoRa Serial Port")
    parser.add_argument("--api", default='http://localhost:5000/api/telemetry', help="Obs Center API URL")
    parser.add_argument("--public-api", default=None, help="Public PHP Dashboard Sink URL")
    parser.add_argument("--web-port", type=int, default=5001, help="Port for Command API")
    args = parser.parse_args()

    bridge_instance = OnshoreBridge(port=args.port, api_url=args.api, public_api=args.public_api)
    if bridge_instance.connect():
        # Start listener thread
        listener_thread = threading.Thread(target=bridge_instance.listen_forever, daemon=True)
        listener_thread.start()

        # Start Flask API
        print(f"Starting Gateway Command API on port {args.web_port}")
        app.run(host='0.0.0.0', port=args.web_port)
