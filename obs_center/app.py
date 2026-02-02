from flask import Flask, render_template, jsonify, request
import random
import time

app = Flask(__name__)

# Mock Data Storage
system_state = {
    "main": {
        "online": True,
        "tds": 0,
        "voltage": 12.6,
        "relay": "OFF",
        "last_update": time.time()
    },
    "health": {
        "online": True,
        "temp": 35.5,
        "uptime": "0d 4h 22m",
        "last_update": time.time()
    }
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/telemetry', methods=['GET'])
def get_telemetry():
    # Update simulation data
    system_state["main"]["tds"] = random.randint(300, 500)
    system_state["main"]["voltage"] = round(random.uniform(12.2, 12.8), 2)
    system_state["main"]["last_update"] = time.time()
    
    system_state["health"]["temp"] = round(random.uniform(34.0, 38.0), 1)
    system_state["health"]["last_update"] = time.time()
    
    return jsonify(system_state)

@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.json
    target = data.get("target")
    cmd = data.get("cmd")
    
    print(f"COMMAND RECEIVED: Target={target}, Cmd={cmd}")
    
    if target == "main" and cmd in ["RELAY_ON", "RELAY_OFF"]:
        system_state["main"]["relay"] = "ON" if cmd == "RELAY_ON" else "OFF"
        return jsonify({"status": "success", "message": f"Relay set to {system_state['main']['relay']}"})
    
    return jsonify({"status": "error", "message": "Invalid command"}), 400

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
