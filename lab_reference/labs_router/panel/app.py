import os
import subprocess
import re
from flask import Flask, render_template, request, jsonify, redirect, url_for

app = Flask(__name__)

HOSTAPD_CONF = "/etc/hostapd/hostapd.conf"
DNSMASQ_LEASES = "/var/lib/misc/dnsmasq.leases"
CLIENT_INTERFACE = "wlx005a8f315136"

def run_command(command):
    try:
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        return True, result.stdout.strip()
    except subprocess.CalledProcessError as e:
        return False, e.stderr.strip()

def get_hotspot_config():
    config = {"ssid": "", "password": ""}
    if os.path.exists(HOSTAPD_CONF):
        with open(HOSTAPD_CONF, "r") as f:
            content = f.read()
            ssid_match = re.search(r'^ssid=(.+)$', content, re.MULTILINE)
            pass_match = re.search(r'^wpa_passphrase=(.+)$', content, re.MULTILINE)
            if ssid_match:
                config["ssid"] = ssid_match.group(1)
            if pass_match:
                config["password"] = pass_match.group(1)
    return config

def set_hotspot_config(ssid, password):
    if not os.path.exists(HOSTAPD_CONF):
        return False, "Config file not found"
    
    with open(HOSTAPD_CONF, "r") as f:
        lines = f.readlines()
    
    new_lines = []
    for line in lines:
        if line.startswith("ssid="):
            new_lines.append(f"ssid={ssid}\n")
        elif line.startswith("wpa_passphrase="):
            new_lines.append(f"wpa_passphrase={password}\n")
        else:
            new_lines.append(line)
            
    with open(HOSTAPD_CONF, "w") as f:
        f.writelines(new_lines)
        
    # Restart hostapd
    success, msg = run_command("systemctl restart hostapd")
    return success, msg

def get_connected_clients():
    clients = []
    if os.path.exists(DNSMASQ_LEASES):
        with open(DNSMASQ_LEASES, "r") as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 4:
                    clients.append({
                        "expiry": parts[0],
                        "mac": parts[1],
                        "ip": parts[2],
                        "hostname": parts[3]
                    })
    return clients

def scan_wifi_networks():
    # SSID, SIGNAL, BARS, SECURITY, IN-USE
    cmd = f"nmcli -t -f SSID,SIGNAL,BARS,SECURITY,IN-USE dev wifi list ifname {CLIENT_INTERFACE}"
    success, output = run_command(cmd)
    networks = []
    if success:
        for line in output.split('\n'):
            if not line: continue
            # nmcli -t escapes colons with backslash, need to handle that if splitting by :
            # But simple split usually works for simple SSIDs. 
            # A more robust regex is safer.
            # Format: SSID:SIGNAL:BARS:SECURITY:IN-USE
            parts = line.split(':')
            if len(parts) >= 5:
                # Re-join the first parts if SSID contained colons (simplistic approach)
                # Better: use the escaped parsing. 
                # For now assuming simple SSIDs or relying on the last 4 fields being fixed.
                in_use = parts[-1]
                security = parts[-2]
                bars = parts[-3]
                signal = parts[-4]
                ssid = ":".join(parts[:-4])
                
                if ssid: # Filter empty SSIDs
                    networks.append({
                        "ssid": ssid,
                        "signal": signal,
                        "bars": bars,
                        "security": security,
                        "connected": in_use == "*"
                    })
    return networks

@app.route('/')
def index():
    hotspot = get_hotspot_config()
    clients = get_connected_clients()
    return render_template('index.html', hotspot=hotspot, clients=clients)

@app.route('/api/scan')
def api_scan():
    networks = scan_wifi_networks()
    return jsonify(networks)

@app.route('/api/connect', methods=['POST'])
def api_connect():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    
    if not ssid:
        return jsonify({"success": False, "message": "No SSID provided"})
    
    cmd = f"nmcli dev wifi connect '{ssid}' password '{password}' ifname {CLIENT_INTERFACE}"
    success, output = run_command(cmd)
    return jsonify({"success": success, "message": output})

@app.route('/api/hotspot', methods=['POST'])
def api_update_hotspot():
    data = request.json
    ssid = data.get('ssid')
    password = data.get('password')
    
    if not ssid or len(password) < 8:
        return jsonify({"success": False, "message": "Invalid Input. Password must be >= 8 chars."})
        
    success, msg = set_hotspot_config(ssid, password)
    return jsonify({"success": success, "message": msg})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80, debug=True)
