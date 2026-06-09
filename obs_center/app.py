import os
import sys
import io
import math
import time
import json
import ftplib
import logging
import sqlite3
import threading
import base64
import re
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, session, Response

# DO mg/L is derived from probe saturation% + water temperature + salinity.
# Salinity comes from the EZO-EC when firmware exposes it, otherwise from this
# env var. Default 30 (open-ocean / Sagres). Override to 0 for freshwater lab
# work (OP_SALINITY_PPT=0 in the systemd unit).
DEFAULT_SALINITY_PPT = float(os.environ.get('OP_SALINITY_PPT', '30'))


# LiFePO4 12V (4S) rested voltage -> SOC% lookup. Source: composite of Victron,
# Battle Born and Renogy published curves for nominal 12.8 V LFP packs.
# Used as a sanity-check on the SmartShunt coulomb-counter, which drifts after
# unsynchronised disconnections (e.g. transplant work). Note: under load the
# pack sags ~0.1-0.3 V depending on current — readings during discharge will
# underestimate true SOC. Most reliable at idle and at the extremes (>90, <20).
LIFEPO4_12V_SOC_CURVE = [
    (13.40, 100), (13.30, 95), (13.20, 80), (13.10, 60),
    (13.00, 40),  (12.95, 30), (12.90, 25), (12.85, 20),
    (12.80, 17),  (12.75, 15), (12.70, 12), (12.65, 10),
    (12.50,  8),  (12.30,  5), (12.00,  2), (10.00,  0),
]

def lifepo4_soc_from_v(v):
    """Linear interpolate SOC% from rested battery voltage using LIFEPO4 curve.
    Returns None if v is None or out of range guards trip."""
    if v is None:
        return None
    try:
        v = float(v)
    except (TypeError, ValueError):
        return None
    if v >= LIFEPO4_12V_SOC_CURVE[0][0]:
        return 100.0
    if v <= LIFEPO4_12V_SOC_CURVE[-1][0]:
        return 0.0
    for i in range(len(LIFEPO4_12V_SOC_CURVE) - 1):
        v_hi, s_hi = LIFEPO4_12V_SOC_CURVE[i]
        v_lo, s_lo = LIFEPO4_12V_SOC_CURVE[i + 1]
        if v_lo <= v <= v_hi:
            frac = (v - v_lo) / (v_hi - v_lo) if v_hi != v_lo else 0
            return round(s_lo + frac * (s_hi - s_lo), 1)
    return None


def compute_do_mgL(sat_pct, T_C, S_PSU, P_kPa=101.325):
    """O2 saturation% -> mg/L via Garcia & Gordon (1992) refit of Benson & Krause.
    Accurate to ~0.1% across full ocean range. The standard used by NOAA, USGS,
    and oceanographic instruments. Returns None if any input is invalid."""
    try:
        Ts = math.log((298.15 - T_C) / (273.15 + T_C))
        lnC = (2.00907 + 3.22014 * Ts + 4.0501 * Ts ** 2 + 4.94457 * Ts ** 3
               - 0.256847 * Ts ** 4 + 3.88767 * Ts ** 5
               - S_PSU * (0.00624523 + 0.00737614 * Ts
                          + 0.010341 * Ts ** 2 + 0.00817083 * Ts ** 3)
               - 4.88682e-7 * S_PSU ** 2)
        C_sat_mgL = math.exp(lnC) * 1.4276  # ml/L -> mg/L
        return round((sat_pct / 100.0) * C_sat_mgL * (P_kPa / 101.325), 2)
    except (TypeError, ValueError):
        return None

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("OpsCenter")

# Database Path — use local data/ dir (works on lab-center without _cortex/)
DB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
os.makedirs(DB_DIR, exist_ok=True)
DB_PATH = os.path.join(DB_DIR, 'telemetry.db')

# Ensure we can import from bridge directory
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bridge.main_bridge import MainBridge
from bridge.health_bridge import HealthBridge
from bridge.lora_handler import LoraHandler

# --- Persistence Helpers ---

def init_db():
    """Create tables if they don't exist."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("CREATE TABLE IF NOT EXISTS telemetry (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, target TEXT, data TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS alerts (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, score REAL, data TEXT)")
        c.execute("CREATE TABLE IF NOT EXISTS activity_log (id INTEGER PRIMARY KEY AUTOINCREMENT, ts REAL, ip TEXT, user TEXT, role TEXT, action TEXT, detail TEXT)")
        conn.commit()
        conn.close()
        logger.info(f"Database initialized at {DB_PATH}")
    except Exception as e:
        logger.error(f"Database init error: {e}")

init_db()


def save_telemetry_to_db(target, data):
    """Saves telemetry payload to SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO telemetry (ts, target, data) VALUES (?, ?, ?)",
                  (time.time(), target, json.dumps(data)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database error (telemetry): {e}")


# ---------------------------------------------------------------------------
# Heartbeat tracking — rolling deque of recent packet arrival timestamps
# per LoRa source. Used by /api/heartbeat for the dashboard latency strip.
# Sources mirror the physical LoRa origin, not logical circuit:
#   main   = M:STATUS packets from Main Pi
#   health = H:STATUS + P:STATUS packets from Health Pi (same bridge process)
# ---------------------------------------------------------------------------
from collections import deque
HEARTBEAT_KEEP = 60   # last N arrivals per source (~30 min at 30s cadence)

heartbeat = {
    "main":   deque(maxlen=HEARTBEAT_KEEP),
    "health": deque(maxlen=HEARTBEAT_KEEP),
}

def note_heartbeat(target):
    """Record a packet arrival. Power packets are attributed to 'health' since
    they originate from the same Health Pi bridge as H:STATUS."""
    if target in ("main", "health"):
        heartbeat[target].append(time.time())
    elif target == "power":
        heartbeat["health"].append(time.time())

def save_alert_to_db(score, data):
    """Saves vision alert to SQLite."""
    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("INSERT INTO alerts (ts, score, data) VALUES (?, ?, ?)",
                  (time.time(), score, json.dumps(data)))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Database error (alert): {e}")


def log_activity(action, detail="", req=None):
    """Log panel activity with IP and user info (SPEC-028 Section 6)."""
    try:
        if req is None:
            req = request
        ip = req.headers.get('X-Forwarded-For', req.remote_addr)
        user = session.get('user', 'anonymous')
        role = session.get('role', 'none')
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "INSERT INTO activity_log (ts, ip, user, role, action, detail) VALUES (?, ?, ?, ?, ?, ?)",
            (time.time(), ip, user, role, action, detail)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Activity log error: {e}")

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
# Secrets are loaded from environment (see ops/secrets.env, wired in via systemd
# EnvironmentFile). If OP_FLASK_SECRET is missing we generate a random ephemeral
# key so dev sessions still work; running without it in prod will invalidate all
# tokens on restart, which is the intended failure mode.
app.secret_key = os.environ.get('OP_FLASK_SECRET') or os.urandom(32).hex()
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=365)
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SECURE'] = False  # Tailscale Funnel terminates TLS before reaching Flask

# --- Access Control (SPEC-028) ---
# All admins share one password (OP_ADMIN_PASS). OP_ADMIN_USERS is a
# comma-separated list of usernames allowed to log in.
_admin_users_env = os.environ.get('OP_ADMIN_USERS', '')
_admin_pass = os.environ.get('OP_ADMIN_PASS', '')
VALID_USERS = {
    u.strip(): _admin_pass
    for u in _admin_users_env.split(',')
    if u.strip() and _admin_pass
}
if not VALID_USERS:
    logger.warning(
        "No admin users configured. Set OP_ADMIN_USERS and OP_ADMIN_PASS "
        "in ops/secrets.env to enable login."
    )

# Token-based auth (Tailscale Funnel doesn't forward cookies reliably)
import hashlib
AUTH_TOKENS = {}  # token -> {user, role, created}

def make_token(username):
    """Generate a persistent auth token for a user."""
    raw = f"{username}:{app.secret_key}:oceanpulse"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]

def get_auth_user():
    """Get current user from token header or Flask session."""
    # Check X-Auth-Token header first (Funnel-safe)
    token = request.headers.get('X-Auth-Token')
    if token and token in AUTH_TOKENS:
        return AUTH_TOKENS[token]
    # Fallback to Flask session
    if session.get('user'):
        return {'user': session['user'], 'role': session['role']}
    return None

# Pre-generate tokens for known users
for _u in VALID_USERS:
    _t = make_token(_u)
    AUTH_TOKENS[_t] = {'user': _u, 'role': 'admin', 'created': time.time()}
    logger.info(f"Auth token ready for {_u}")

# Public dashboard FTP relay
PUBLIC_FTP_HOST = os.environ.get("OP_FTP_HOST", "ftp.oceanpulse.pt")
PUBLIC_FTP_USER = os.environ.get("OP_FTP_USER", "oceanpul")
PUBLIC_FTP_PASS = os.environ.get("OP_FTP_PASS", "")
PUBLIC_FTP_PATH = "public_html/dashboard"

# System Configurations (Tailscale IPs from MEMORY_BANK.md).
# All four Pis share one SSH password (OP_PI_SSH_PASS in ops/secrets.env).
_PI_PASS = os.environ.get("OP_PI_SSH_PASS", "")
SYSTEMS = {
    "main": {
        "host": "100.115.88.91",
        "user": "lab",
        "pass": _PI_PASS,
        "bridge_path": "~/oceanpulse/bridge/main_bridge.py",
        "port": "/dev/ttyACM0"
    },
    "health": {
        "host": "100.116.100.92",
        "user": "router",
        "pass": _PI_PASS,
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
        "pass": _PI_PASS
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
        "ec": None,
        "do": None,           # mg/L — derived from do_sat + water_temp + salinity
        "do_sat": None,       # % saturation — the actual probe measurement
        "salinity": None,     # PSU; from Atlas EZO-EC (when firmware exposes it)
        "water_temp": None,
        "voltage": None,
        "distance": None,
        "relay": "OFF",
        "watchdog": "OFF",
        "shell_ack": None,        # SPEC-026: LoRa Remote Shell ACK
        # SPEC-035: UV safety interlock state, sourced from the Mega via SAFETY:GET.
        "brake": None,            # "ON" (UV cut) | "OFF" (allowed) | None (unknown)
        "safety": {
            "heat_armed": None,
            "dist_armed": None,
            "dist_thr_cm": None,
            "dist_hyst_cm": None,
            "dist_clr_ms": None,
            "heat_clr_ms": None,
            "boot_lock": None,
            "dist_trip": None,
            "heat_trip": None,
            "last_fetch": 0,
        },
        "last_update": 0
    },
    "health": {
        "online": False,
        "temp": None,
        "hum": None,
        "dht1_temp": None,
        "dht1_hum": None,
        "dht2_temp": None,
        "dht2_hum": None,
        "dht3_temp": None,
        "dht3_hum": None,
        "dht4_temp": None,
        "dht4_hum": None,
        "voltage": None,
        "uptime": "N/A",
        "shell_ack": None,        # SPEC-026
        "last_update": 0
    },
    "gateway": {
        "online": False,
        "last_update": 0
    },
    # SPEC-036: Power subsystem (MPPT + SmartShunt over LoRa P:STATUS).
    # Populated by onshore_bridge via /api/telemetry target=power.
    "power": {
        "online": False,
        "last_update": 0,
        "mppt": {
            "panel_v": None,    # V (decivolts on wire -> V)
            "panel_w": None,    # W
            "charge_i": None,   # A
            "load_i": None,     # A (MPPT LOAD output)
            "cs": None,         # int 0..7
            "cs_name": None,    # human-readable from CS_NAMES
            "err": None,        # int (0 = no error)
        },
        "shunt": {
            "batt_v": None,     # V
            "batt_i": None,     # A (signed; negative = discharging)
            "batt_p": None,     # W (signed)
            "soc": None,        # % (one decimal)
            "ttg_min": None,    # minutes (-1 = ∞)
        },
        "derived": {
            "solar_in_w": None,
            "to_battery_w": None,
            "to_load_output_w": None,
            "direct_loads_w": None,
            "soc_from_v": None,        # SOC% derived from batt_v via LIFEPO4 curve
            "soc_divergence": None,    # |shunt.soc - derived.soc_from_v|
            "soc_synced": True,        # False when divergence > SOC_DRIFT_THRESHOLD
        },
    },
    "vision": {
        "online": False,
        "last_alert_score": 0,
        "last_alert_time": 0,
        "alerts": [],        # rolling list of last 10 alerts
        "alert_count": 0,
        "snapshot_b64": None,
        "snapshot_time": 0,
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
    # Mark systems offline if no update received in 60s (LoRa TX cycle is ~35s)
    now = time.time()
    for key in ("main", "health", "gateway", "vision", "power"):
        # SPEC-036: P:STATUS cadence is 30s; allow 3 misses (90s) before offline.
        threshold = 120 if key == "vision" else (90 if key == "power" else 60)
        if now - system_state[key]["last_update"] > threshold:
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


@app.route('/api/session', methods=['GET'])
def get_session():
    """Return current session state."""
    auth = get_auth_user()
    if auth:
        return jsonify({"user": auth['user'], "role": auth['role']})
    return jsonify({"user": None, "role": None})


@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    username = (data.get("username") or "").strip().lower()
    password = data.get("password") or ""

    if username in VALID_USERS and VALID_USERS[username] == password:
        session.permanent = True
        session['user'] = username
        session['role'] = 'admin'
        token = make_token(username)
        logger.info(f"Login: {username} (admin), token issued")
        log_activity("login_success", username)
        return jsonify({"status": "success", "user": username, "role": "admin", "token": token})

    logger.warning(f"Failed login attempt: {username}")
    log_activity("login_failed", username)
    return jsonify({"status": "error", "message": "Invalid credentials"}), 401


@app.route('/api/logout', methods=['POST'])
def logout():
    user = session.pop('user', None)
    session.pop('role', None)
    logger.info(f"Logout: {user}")
    log_activity("logout", user or "unknown")
    return jsonify({"status": "success"})


@app.route('/api/guest', methods=['POST'])
def enter_guest():
    session['user'] = 'guest'
    session['role'] = 'guest'
    log_activity("guest_entry")
    return jsonify({"status": "success", "user": "guest", "role": "guest"})


@app.route('/api/telemetry', methods=['GET', 'POST'])
def handle_telemetry():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON body"}), 400

        target = data.get("target")
        payload = data.get("data", {})
        logger.info(f"Received telemetry for {target}: {payload}")

        if target not in system_state:
            return jsonify({"status": "error", "message": f"Unknown target '{target}'"}), 400

        # Persistent storage (REQ-050)
        save_telemetry_to_db(target, payload)

        # Heartbeat tracking for the dashboard latency strip
        note_heartbeat(target)

        # Update specific fields (only known keys)
        for key, value in payload.items():
            if key in system_state[target]:
                logger.info(f"Updating {target}.{key} = {value}")
                system_state[target][key] = value
            else:
                logger.warning(f"Key '{key}' not in system_state['{target}']")

        # Gateway can also report LoRa link status
        if target == "gateway":
            if "lora_connected" in payload:
                system_state["lora"]["connected"] = payload["lora_connected"]
            if "rssi" in payload:
                system_state["lora"]["last_rssi"] = payload["rssi"]
            if "snr" in payload:
                system_state["lora"]["last_snr"] = payload["snr"]

        # Derive DO mg/L from saturation% + water temp + salinity using
        # Garcia-Gordon. Live salinity from the probe is preferred; otherwise
        # the configured default is used.
        if target == "main":
            m = system_state["main"]
            if m.get("do_sat") is not None and m.get("water_temp") is not None:
                s_ppt = m["salinity"] if m.get("salinity") is not None else DEFAULT_SALINITY_PPT
                m["do"] = compute_do_mgL(m["do_sat"], m["water_temp"], s_ppt)

        # SPEC-036: Power telemetry — payload arrives as {"mppt": {...}, "shunt": {...}}
        # rather than flat keys. Merge into the nested system_state.power and
        # compute derived power-flow fields.
        if target == "power":
            p = system_state["power"]
            mppt_in = payload.get("mppt") or {}
            shunt_in = payload.get("shunt") or {}
            for k, v in mppt_in.items():
                if k in p["mppt"]:
                    p["mppt"][k] = v
            for k, v in shunt_in.items():
                if k in p["shunt"]:
                    p["shunt"][k] = v
            # Decode CS to human-readable
            CS_NAMES = {0: "Off", 2: "Fault", 3: "Bulk", 4: "Absorption",
                        5: "Float", 6: "Storage", 7: "Equalize"}
            cs = p["mppt"].get("cs")
            p["mppt"]["cs_name"] = CS_NAMES.get(cs, f"?{cs}" if cs is not None else None)
            # Derived power-flow (W) from raw fields
            sv = p["shunt"].get("batt_v")
            ci = p["mppt"].get("charge_i")
            li = p["mppt"].get("load_i")
            pw = p["mppt"].get("panel_w")
            sp = p["shunt"].get("batt_p")
            d = p["derived"]
            d["solar_in_w"]       = pw if pw is not None else None
            d["to_battery_w"]     = round(ci * sv) if (ci is not None and sv is not None) else None
            d["to_load_output_w"] = round(li * sv) if (li is not None and sv is not None) else None
            # direct_loads_w = battery-side loads NOT going through MPPT LOAD.
            # Visible only when battery is net-discharging (sp < 0).
            d["direct_loads_w"]   = max(0, -sp) if sp is not None else None
            # Voltage-derived SOC sanity check against shunt's coulomb counter.
            # Flag drift when |shunt - voltage| > 30 percentage points.
            soc_v = lifepo4_soc_from_v(sv)
            soc_shunt = p["shunt"].get("soc")
            d["soc_from_v"] = soc_v
            if soc_v is not None and soc_shunt is not None:
                d["soc_divergence"] = round(abs(soc_shunt - soc_v), 1)
                d["soc_synced"] = d["soc_divergence"] <= 30
            else:
                d["soc_divergence"] = None
                d["soc_synced"] = True

        system_state[target]["online"] = True
        system_state[target]["last_update"] = time.time()
        return jsonify({"status": "success", "message": f"Telemetry updated for {target}"})

    # GET — return current state. Inject server-computed `age_s` per subsystem
    # so the dashboard doesn't have to do clock arithmetic (avoids browser
    # clock-drift causing bogus "Nm ago" displays).
    update_telemetry()
    now = time.time()
    snapshot = dict(system_state)
    for key in ("main", "health", "gateway", "vision", "power"):
        lu = system_state.get(key, {}).get("last_update")
        snapshot[key] = dict(system_state[key])
        snapshot[key]["age_s"] = (now - lu) if lu else None
    snapshot["server_ts"] = now
    return jsonify(snapshot)


@app.route('/ar/metrics', methods=['GET'])
def ar_metrics():
    # SPEC-037: read-only passthrough for the AR beer-mat project.
    # Flat JSON, raw values, None fields omitted, CORS open, no auth.
    # Public via Tailscale Funnel.
    update_telemetry()
    m = system_state["main"]
    p_mppt = system_state["power"]["mppt"]
    p_shunt = system_state["power"]["shunt"]
    p_derived = system_state["power"]["derived"]
    h = system_state["health"]

    def drop_none(d):
        return {k: v for k, v in d.items() if v is not None}

    body = {
        "ts": datetime.utcnow().isoformat(timespec="seconds") + "Z",
        "main": drop_none({
            "ec":            m.get("ec"),
            "salinity_psu":  m.get("salinity"),
            "do_sat":        m.get("do_sat"),
            "do_mgL":        m.get("do"),
            "water_temp_c":  m.get("water_temp"),
            "distance_cm":   m.get("distance"),
        }),
        "power": drop_none({
            "batt_v":        p_shunt.get("batt_v"),
            "soc_pct":       p_shunt.get("soc"),
            "solar_w":       p_derived.get("solar_in_w"),
            "charge_state":  p_mppt.get("cs_name"),
        }),
        "health": drop_none({
            "compute_temp_c": h.get("temp"),
            "compute_hum_pct": h.get("hum"),
        }),
    }
    body = {k: v for k, v in body.items() if k == "ts" or v}

    resp = jsonify(body)
    resp.headers["Cache-Control"] = "public, max-age=5"
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET"
    return resp


@app.route('/api/heartbeat', methods=['GET'])
def get_heartbeat():
    """Return recent packet arrival timestamps + inter-arrival latencies per
    LoRa source. The dashboard strip uses this to draw the latency sparkline.

    Output format:
      {
        "server_ts": <unix>,
        "sources": {
          "main":   {"arrivals": [t1, t2, ...], "latencies_s": [t2-t1, ...], "last_age_s": float|null},
          "health": {...}
        }
      }
    """
    now = time.time()
    out = {"server_ts": now, "sources": {}}
    for src in ("main", "health"):
        arrivals = list(heartbeat[src])
        latencies = [arrivals[i] - arrivals[i-1] for i in range(1, len(arrivals))]
        last_age = (now - arrivals[-1]) if arrivals else None
        out["sources"][src] = {
            "arrivals":    arrivals,
            "latencies_s": latencies,
            "last_age_s":  last_age,
            "count":       len(arrivals),
        }
    return jsonify(out)


@app.route('/api/telemetry/history', methods=['GET'])
def get_telemetry_history():
    """Retrieve historical telemetry (last N hours). Default: 48h."""
    hours = request.args.get('hours', 48, type=int)
    target = request.args.get('target')
    since = time.time() - (hours * 3600)

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        if target:
            c.execute("SELECT ts, data FROM telemetry WHERE ts > ? AND target = ? ORDER BY ts DESC", (since, target))
        else:
            c.execute("SELECT ts, target, data FROM telemetry WHERE ts > ? ORDER BY ts DESC", (since,))
        
        rows = c.fetchall()
        history = []
        for row in rows:
            if target:
                history.append({"ts": row[0], "data": json.loads(row[1])})
            else:
                history.append({"ts": row[0], "target": row[1], "data": json.loads(row[2])})
        
        conn.close()
        return jsonify({"status": "success", "hours": hours, "count": len(history), "history": history})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/command', methods=['POST'])
def send_command():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    target = data.get("target")
    cmd = data.get("cmd")

    if not target or not cmd:
        return jsonify({"status": "error", "message": "Missing 'target' or 'cmd'"}), 400

    if cmd not in ("REBOOT", "SOFT_REBOOT", "RELAY_ON", "RELAY_OFF"):
        return jsonify({"status": "error", "message": f"Unsupported command: {cmd}"}), 400

    log_activity("command", f"{target}:{cmd}")

    # Step 1: Try Gateway API (LoRa mission protocol)
    if HAS_REQUESTS:
        target_prefix = "M" if target == "main" else "H"

        if cmd == "SOFT_REBOOT":
            lora_cmd = "SOFT_REBOOT"
            lora_param = None
        elif cmd == "REBOOT":
            lora_cmd = "REBOOT"
            lora_param = None
        else:
            lora_cmd = "RELAY"
            lora_param = "ON" if cmd == "RELAY_ON" else "OFF"

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

    # SOFT_REBOOT is LoRa-only — no SSH fallback (per SPEC-025)
    if cmd == "SOFT_REBOOT":
        return jsonify({"status": "error", "message": f"SOFT_REBOOT for {target} failed (Gateway unreachable)"}), 503

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


@app.route('/api/cal/ec', methods=['POST'])
def cal_ec():
    """SPEC-034 — Atlas EZO-EC calibration passthrough.

    Forwards an Atlas command (Cal,dry / Cal,low,N / Cal,high,N / O,S,1 /
    Cal,? / R / Status / i / K,? / Cal,clear) to the Main bridge command
    proxy on port 5051 as EC:CMD:<text>:<timeout_ms>. Admin-only.

    Request body: {"command": "<atlas>", "timeout_ms": <int>}
    Response: {"status": "success"|"error",
               "atlas_status": "<*OK>", "atlas_reply": "<probe reply>",
               "raw": "<raw firmware response>"}
    """
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin login required"}), 403

    data = request.json or {}
    atlas_cmd = (data.get('command') or '').strip()
    timeout_ms = int(data.get('timeout_ms') or 1200)

    if not atlas_cmd:
        return jsonify({"status": "error", "message": "Missing 'command'"}), 400
    # Whitelist Atlas verbs to keep the surface narrow. EZO-EC command set:
    # Cal | O | R | Status | i | K | T | TDS | Find | Sleep | Plock | Export | Import | Name | L | Factory
    allowed_prefixes = ('cal', 'o,', 'o ', 'o?', 'r', 'status', 'i', 'k', 't,', 't?',
                        'tds', 'find', 'sleep', 'plock', 'export', 'import', 'name', 'l,', 'factory')
    if not any(atlas_cmd.lower().startswith(p) or atlas_cmd.lower() == p.rstrip(',? ') for p in allowed_prefixes):
        return jsonify({"status": "error", "message": f"Command not whitelisted: {atlas_cmd}"}), 400
    if timeout_ms < 200 or timeout_ms > 30000:
        return jsonify({"status": "error", "message": "timeout_ms out of range (200-30000)"}), 400

    bridge_cmd = f"EC:CMD:{atlas_cmd}:{timeout_ms}"
    log_activity("cal_ec", atlas_cmd)

    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library unavailable on obs_center"}), 500

    # Main Pi command proxy on port 5051
    main_host = SYSTEMS.get('main', {}).get('host')
    if not main_host:
        return jsonify({"status": "error", "message": "Main host not configured"}), 500
    proxy_url = f"http://{main_host}:5051/cmd"
    try:
        # Proxy timeout = command timeout + 2s slack for HTTP overhead
        res = http_requests.post(proxy_url, json={"command": bridge_cmd},
                                 timeout=(timeout_ms / 1000.0) + 3.0)
    except Exception as e:
        return jsonify({"status": "error",
                        "message": f"Main bridge proxy unreachable: {e}"}), 502
    if res.status_code != 200:
        return jsonify({"status": "error",
                        "message": f"Proxy HTTP {res.status_code}: {res.text[:200]}"}), 502

    proxy_json = res.json() if res.headers.get('content-type', '').startswith('application/json') else {}
    raw = (proxy_json.get('value') or '').strip() or (proxy_json.get('raw') or '').strip()
    # Firmware reply pattern: "EC:CMD:OK:<status>:<reply>"  e.g. "EC:CMD:OK:*OK:?CAL,2"
    atlas_status = ''
    atlas_reply = ''
    if raw.startswith('EC:CMD:'):
        parts = raw.split(':', 3)
        # parts[0]='EC', [1]='CMD', [2]='OK'|'ERR', [3]='<status>:<reply>'
        if len(parts) >= 4:
            tail = parts[3]
            # tail = "<atlas_status>:<atlas_reply>"
            tparts = tail.split(':', 1)
            atlas_status = tparts[0].strip()
            atlas_reply = tparts[1].strip() if len(tparts) > 1 else ''
        ok = parts[2].upper() == 'OK' if len(parts) >= 3 else False
        return jsonify({"status": "success" if ok else "error",
                        "atlas_status": atlas_status,
                        "atlas_reply": atlas_reply,
                        "raw": raw}), 200
    # Fallback — pass whatever we got
    return jsonify({"status": "success" if proxy_json.get('status') == 'success' else "error",
                    "atlas_reply": raw, "raw": raw, "proxy": proxy_json}), 200


@app.route('/api/cal/do', methods=['POST'])
def cal_do():
    """SPEC-034 — Optical DO sensor calibration / config passthrough.

    Forwards a DO:* command to the Main bridge command proxy (port 5051),
    which dispatches it to the DOSensor Modbus driver. Admin-only.

    Supported commands (case-insensitive):
        DO:READ                       — read DO sat / mgL / water_temp now
        DO:CAL:SAT                    — calibrate 100% saturation (probe in air ~1cm above water)
        DO:CAL:ZERO                   — calibrate zero (probe in 5% Na2SO3 solution)
        DO:SAL:GET / DO:SAL:SET:<n>   — read/write salinity ‰ (register 0x1020)
        DO:PRESS:GET / DO:PRESS:SET:<n>  — read/write atm pressure ×100 (register 0x1022)
        DO:ADDR:GET / DO:BAUD:GET     — read configured Modbus addr / baud index

    Request: {"command": "DO:..."}
    Response: passthrough of bridge JSON.
    """
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin login required"}), 403

    data = request.json or {}
    cmd = (data.get('command') or '').strip()
    if not cmd or not cmd.upper().startswith('DO:'):
        return jsonify({"status": "error", "message": "Missing or non-DO command"}), 400

    allowed = {'DO:READ', 'DO:CAL:SAT', 'DO:CAL:ZERO',
               'DO:SAL:GET', 'DO:PRESS:GET', 'DO:ADDR:GET', 'DO:BAUD:GET'}
    cmd_upper = cmd.upper()
    if cmd_upper not in allowed and not cmd_upper.startswith(('DO:SAL:SET:', 'DO:PRESS:SET:')):
        return jsonify({"status": "error", "message": f"Command not whitelisted: {cmd}"}), 400

    log_activity("cal_do", cmd)

    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library unavailable"}), 500
    main_host = SYSTEMS.get('main', {}).get('host')
    if not main_host:
        return jsonify({"status": "error", "message": "Main host not configured"}), 500
    try:
        res = http_requests.post(f"http://{main_host}:5051/cmd",
                                 json={"command": cmd}, timeout=6.0)
    except Exception as e:
        return jsonify({"status": "error",
                        "message": f"Main bridge proxy unreachable: {e}"}), 502
    if res.status_code != 200:
        return jsonify({"status": "error",
                        "message": f"Proxy HTTP {res.status_code}: {res.text[:200]}"}), 502
    try:
        return jsonify(res.json()), 200
    except Exception:
        return jsonify({"status": "error", "message": f"non-json: {res.text[:200]}"}), 502


@app.route('/api/shell/execute', methods=['POST'])
def shell_execute():
    """SPEC-026 — LoRa Remote Shell (Emergency Access).
    Admin-only. Validates against whitelist, encodes to B64, sends to Gateway.
    """
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin login required"}), 403

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    target = data.get("target")
    cmd = data.get("cmd")

    if not target or not cmd:
        return jsonify({"status": "error", "message": "Missing 'target' or 'cmd'"}), 400

    # Whitelist (identical to buoy_bridge.py for consistency)
    WHITELIST = [
        r'^nmcli\s+.*$',
        r'^ip\s+addr\s+.*$',
        r'^ip\s+route\s+.*$',
        r'^ping\s+-c\s+.*$',
        r'^systemctl\s+.*\s+oceanpulse.*$',
        r'^systemctl\s+restart\s+buoy-bridge-.*$',
        r'^reboot$',
        r'^uptime$',
        r'^free\s+-m$',
        r'^df\s+-h$',
        r'^lsusb$',
        r'^tail\s+-n\s+\d+\s+.*\.log$'
    ]

    authorized = any(re.match(pattern, cmd) for pattern in WHITELIST)
    if not authorized:
        return jsonify({"status": "error", "message": "Command not in whitelist"}), 400

    log_activity("shell_execute", f"{target}:{cmd}")

    # Generate random CMD_ID
    import random
    cmd_id = f"{random.randint(100, 999)}"

    # Encode to Base64
    b64_cmd = base64.b64encode(cmd.encode('utf-8')).decode()

    # Send to Gateway
    if HAS_REQUESTS:
        try:
            res = http_requests.post(
                SYSTEMS["gateway"]["api_url"],
                json={
                    "target": "M" if target == "main" else "H",
                    "cmd": "SHELL",
                    "param": f"{cmd_id}:{b64_cmd}"
                },
                timeout=15 # Higher timeout for LoRa TX
            )
            if res.status_code == 200:
                return jsonify({
                    "status": "success", 
                    "cmd_id": cmd_id, 
                    "message": f"Command sent via LoRa (ID: {cmd_id}). Awaiting response..."
                })
            else:
                return jsonify({"status": "error", "message": f"Gateway error: {res.text}"}), 502
        except Exception as e:
            return jsonify({"status": "error", "message": f"Gateway unreachable: {e}"}), 503

    return jsonify({"status": "error", "message": "Requests library not available"}), 500


# --- SPEC-035: UV Hardware Safety Interlock (Pin 30) ---
#
# Backend half of REQ-056. The Mega firmware (v3.6) owns Pin 30 and the rule
# state machine. This surface lets an admin operator query and configure the
# safety rules from the panel without SSH. Wire goes:
#
#   panel UI  ↔  /api/safety/config  ↔  buoy_bridge HTTP proxy (5051)  ↔  Mega
#
# Mega is the source of truth (config persisted in EEPROM). We mirror the
# latest snapshot into system_state["main"]["safety"] for read-side consumers.

_SAFETY_FIELD_BOOL = {"HEAT", "DIST", "BRAKE", "BOOT_LOCK", "DIST_TRIP", "HEAT_TRIP"}
_SAFETY_FIELD_INT  = {"DIST_THR", "DIST_HYST", "DIST_CLR", "HEAT_CLR"}


def _safety_proxy_post(command, timeout=8):
    """Send a single command to the Main Mega via the buoy_bridge HTTP proxy.
    Returns (ok, parsed_json_or_error_str)."""
    if not HAS_REQUESTS:
        return False, "requests library not available"
    cfg = SYSTEMS["main"]
    proxy_url = f"http://{cfg['host']}:5051/cmd"
    try:
        res = http_requests.post(proxy_url, json={"command": command}, timeout=timeout)
        try:
            return True, res.json()
        except ValueError:
            return False, f"non-JSON reply: {res.text[:200]}"
    except http_requests.exceptions.Timeout:
        return False, "bridge proxy timeout"
    except Exception as e:
        return False, f"bridge proxy unreachable: {e}"


def _parse_safety_value(raw_value):
    """Parse the Mega's SAFETY:GET payload (k=v,k=v,...) into a dict.
    Booleans become True/False; integers become ints; everything else stays string."""
    out = {}
    if not raw_value:
        return out
    for part in str(raw_value).split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip().upper()
        v = v.strip()
        if k in _SAFETY_FIELD_BOOL:
            out[k] = (v.upper() == "ON")
        elif k in _SAFETY_FIELD_INT:
            try:
                out[k] = int(v)
            except ValueError:
                out[k] = v
        else:
            out[k] = v
    return out


def _refresh_safety_state():
    """Pull a fresh SAFETY:GET from the Mega and mirror it into system_state.
    Returns (ok, snapshot_dict_or_error_str). Logs BRAKE state changes to activity log."""
    ok, payload = _safety_proxy_post("SAFETY:GET", timeout=8)
    if not ok:
        return False, payload
    if not isinstance(payload, dict) or payload.get("status") != "success":
        return False, payload
    raw = payload.get("value", "")
    parsed = _parse_safety_value(raw)
    if not parsed:
        return False, f"empty/unparseable SAFETY:GET: {raw!r}"

    prior_brake = system_state["main"].get("brake")
    new_brake = "ON" if parsed.get("BRAKE") else "OFF"

    safety = system_state["main"]["safety"]
    safety["heat_armed"]  = parsed.get("HEAT")
    safety["dist_armed"]  = parsed.get("DIST")
    safety["dist_thr_cm"] = parsed.get("DIST_THR")
    safety["dist_hyst_cm"] = parsed.get("DIST_HYST")
    safety["dist_clr_ms"] = parsed.get("DIST_CLR")
    safety["heat_clr_ms"] = parsed.get("HEAT_CLR")
    safety["boot_lock"]   = parsed.get("BOOT_LOCK")
    safety["dist_trip"]   = parsed.get("DIST_TRIP")
    safety["heat_trip"]   = parsed.get("HEAT_TRIP")
    safety["last_fetch"]  = time.time()
    system_state["main"]["brake"] = new_brake

    # Audit any BRAKE transition. Cause-of-trip annotation aids field debugging.
    if prior_brake is not None and prior_brake != new_brake:
        cause = []
        if parsed.get("DIST_TRIP"): cause.append("DIST")
        if parsed.get("HEAT_TRIP"): cause.append("HEAT")
        if parsed.get("BOOT_LOCK"): cause.append("BOOT_LOCK")
        try:
            with app.test_request_context('/'):
                log_activity("safety_brake_change",
                             f"{prior_brake}->{new_brake} cause={'+'.join(cause) or 'none'}")
        except Exception as e:
            logger.warning(f"safety_brake_change log failed: {e}")

    return True, {
        "brake": new_brake,
        "heat_armed":  parsed.get("HEAT"),
        "dist_armed":  parsed.get("DIST"),
        "dist_thr_cm": parsed.get("DIST_THR"),
        "dist_hyst_cm": parsed.get("DIST_HYST"),
        "dist_clr_ms": parsed.get("DIST_CLR"),
        "heat_clr_ms": parsed.get("HEAT_CLR"),
        "boot_lock":   parsed.get("BOOT_LOCK"),
        "dist_trip":   parsed.get("DIST_TRIP"),
        "heat_trip":   parsed.get("HEAT_TRIP"),
        "fetched_at":  safety["last_fetch"],
    }


@app.route('/api/safety/config', methods=['GET'])
def safety_config_get():
    """Return the current SPEC-035 safety interlock state from the Mega.
    Open read (so the dashboard can show BRAKE state to any viewer).
    Mutations are admin-gated via POST."""
    ok, result = _refresh_safety_state()
    if not ok:
        return jsonify({"status": "error", "message": str(result)}), 502
    return jsonify({"status": "success", "config": result})


# Field name → Mega SAFETY:* command formatter. Each formatter receives the
# raw value from the POST body and returns the command string to send.
_SAFETY_POST_DISPATCH = [
    ("heat_armed",   lambda v: f"SAFETY:HEAT:{'ON' if bool(v) else 'OFF'}"),
    ("dist_armed",   lambda v: f"SAFETY:DIST:{'ON' if bool(v) else 'OFF'}"),
    ("dist_thr_cm",  lambda v: f"SAFETY:DIST_THR:{int(v)}"),
    ("dist_hyst_cm", lambda v: f"SAFETY:DIST_HYST:{int(v)}"),
    ("dist_clr_ms",  lambda v: f"SAFETY:DIST_CLR:{int(v)}"),
    ("heat_clr_ms",  lambda v: f"SAFETY:HEAT_CLR:{int(v)}"),
]


@app.route('/api/safety/config', methods=['POST'])
def safety_config_post():
    """Update SPEC-035 safety interlock config on the Mega.

    Body (all fields optional, only present ones are pushed):
      {
        "heat_armed":   bool,
        "dist_armed":   bool,
        "dist_thr_cm":  int (30-500),
        "dist_hyst_cm": int (5-100),
        "dist_clr_ms":  int (500-10000),
        "heat_clr_ms":  int (1000-30000)
      }

    Each field is sent as a separate SAFETY:* command. On any per-field failure
    we collect the error but keep going (Mega EEPROM accepts partial updates).
    After the batch we re-read SAFETY:GET so the caller sees authoritative state.
    Admin-only per SPEC-028 (Panel Access Control)."""
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin authentication required"}), 403

    data = request.json or {}
    if not isinstance(data, dict):
        return jsonify({"status": "error", "message": "JSON object required"}), 400

    applied = []
    errors  = []
    for field, formatter in _SAFETY_POST_DISPATCH:
        if field not in data:
            continue
        try:
            cmd = formatter(data[field])
        except (TypeError, ValueError) as e:
            errors.append({"field": field, "error": f"bad value: {e}"})
            continue
        ok, reply = _safety_proxy_post(cmd, timeout=6)
        if not ok:
            errors.append({"field": field, "command": cmd, "error": str(reply)})
            continue
        # Mega returns {"status":"success","command":"SAFETY","value":"<KEY>=<NEW_VAL>"}
        # or {"status":...,"value":"ERR:..."} on range failure.
        val = ""
        if isinstance(reply, dict):
            val = str(reply.get("value", ""))
        if val.startswith("ERR") or "ERR:" in val:
            errors.append({"field": field, "command": cmd, "error": val})
            continue
        applied.append({"field": field, "command": cmd, "ack": val})
        log_activity("safety_config", f"{field}={data[field]} ack={val}")

    if not applied and not errors:
        return jsonify({"status": "error", "message": "No recognized fields in body"}), 400

    # Authoritative read-back.
    ok, fresh = _refresh_safety_state()
    snapshot = fresh if ok else None

    return jsonify({
        "status": "success" if not errors else "partial",
        "applied": applied,
        "errors": errors,
        "config": snapshot,
    }), (200 if not errors else 207)


# --- Internal Operations Manual (admin-only) ---
#
# Serves ops/SYSTEM_MANUAL.md as raw markdown to admin users. The file is
# .gitignored (contains SSH creds, admin token recipe, FTP passwords) and
# only present on lab-center via direct scp deploy. Frontend renders with
# a client-side markdown library (e.g. marked.js).
MANUAL_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__), '..', 'ops', 'SYSTEM_MANUAL.md'))


@app.route('/api/manual', methods=['GET'])
def get_manual():
    """Return ops/SYSTEM_MANUAL.md raw markdown to admin operators.
    Admin-only (SPEC-028). Logged to activity_log on every fetch."""
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin authentication required"}), 403

    if not os.path.exists(MANUAL_PATH):
        return jsonify({
            "status": "error",
            "message": f"Manual not present at {MANUAL_PATH}. Deploy ops/SYSTEM_MANUAL.md to lab-center.",
        }), 404

    try:
        with open(MANUAL_PATH, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        logger.error(f"Failed to read manual: {e}")
        return jsonify({"status": "error", "message": f"Read failed: {e}"}), 500

    log_activity("manual_view", f"bytes={len(content)}")
    return Response(content, mimetype='text/markdown; charset=utf-8')


@app.route('/api/debug/uv', methods=['POST'])
def debug_uv():
    """SPEC-033 — Debug pin toggle for UV relay (Pin 4 on Main Mega).
    Admin-only. No safety guards. Bench testing only.
    POSTs directly to the buoy_bridge HTTP command proxy on System A
    (Tailscale 100.115.88.91:5051) — no SSH, no paramiko."""
    auth = get_auth_user()
    if not auth or auth.get('role') != 'admin':
        return jsonify({"status": "error", "message": "Admin authentication required"}), 403

    data = request.json or {}
    state = (data.get("state") or "").upper()
    if state not in ("ON", "OFF"):
        return jsonify({"status": "error", "message": "state must be 'ON' or 'OFF'"}), 400

    log_activity("debug_uv", state)

    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not available"}), 500

    cfg = SYSTEMS["main"]
    proxy_url = f"http://{cfg['host']}:5051/cmd"
    try:
        res = http_requests.post(proxy_url, json={"command": f"UV:{state}"}, timeout=10)
        try:
            return jsonify(res.json()), res.status_code
        except ValueError:
            return jsonify({"status": "error", "message": f"Bad reply: {res.text}"}), 502
    except http_requests.exceptions.Timeout:
        return jsonify({"status": "error", "message": "Bridge proxy timeout"}), 504
    except Exception as e:
        return jsonify({"status": "error", "message": f"Bridge proxy unreachable: {e}"}), 502


@app.route('/api/lora/config', methods=['POST'])
def lora_config():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    preset = data.get("preset")
    if not preset:
        return jsonify({"status": "error", "message": "Missing 'preset'"}), 400

    log_activity("lora_config", f"preset:{preset}")
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
    log_activity("lora_test", f"mode:{mode}")

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


# --- Vision API (SPEC-009 Bootstrap) ---

@app.route('/api/vision/alert', methods=['POST'])
def vision_alert():
    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    score = data.get("score", 0)
    timestamp = data.get("timestamp", time.time())
    thumbnail_b64 = data.get("thumbnail_b64", "")

    alert = {
        "score": score,
        "timestamp": timestamp,
        "thumbnail_b64": thumbnail_b64,
        "regions": data.get("regions"),
        "coverage_pct": data.get("coverage_pct"),
        "fluor_pixels": data.get("fluor_pixels")
    }

    # Persistent storage (REQ-050)
    save_alert_to_db(score, alert)

    # Update vision state
    system_state["vision"]["last_alert_score"] = score
    system_state["vision"]["last_alert_time"] = timestamp
    system_state["vision"]["alert_count"] += 1
    system_state["vision"]["online"] = True
    system_state["vision"]["last_update"] = time.time()

    # Insert into alerts list (keep last 10)
    system_state["vision"]["alerts"].insert(0, alert)
    system_state["vision"]["alerts"] = system_state["vision"]["alerts"][:10]

    logger.warning(f"VISION ALERT: Score {score} at {timestamp}")
    return jsonify({"status": "success", "message": "Vision alert recorded"})


@app.route('/api/vision/history', methods=['GET'])
def get_vision_history():
    """Retrieve historical vision alerts (last N hours). Default: 48h."""
    hours = request.args.get('hours', 48, type=int)
    since = time.time() - (hours * 3600)

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ts, score, data FROM alerts WHERE ts > ? ORDER BY ts DESC", (since,))
        
        rows = c.fetchall()
        history = []
        for row in rows:
            history.append({
                "ts": row[0],
                "score": row[1],
                "data": json.loads(row[2])
            })
        
        conn.close()
        return jsonify({"status": "success", "hours": hours, "count": len(history), "history": history})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route('/api/vision/status', methods=['GET'])
def vision_status():
    # Light-weight status (no thumbnails)
    update_telemetry() # ensure staleness check
    v = system_state["vision"]
    
    resp = jsonify({
        "online": v["online"],
        "alert_count": v["alert_count"],
        "last_alert_score": v["last_alert_score"],
        "last_alert_time": v["last_alert_time"]
    })
    resp.headers["Cache-Control"] = "no-store"
    return resp


@app.route('/api/vision/alerts/latest', methods=['GET'])
def vision_alerts_latest():
    # Returns most recent alert including base64 thumbnail
    # Try in-memory first, fall back to database (survives restarts)
    if system_state["vision"]["alerts"]:
        return jsonify(system_state["vision"]["alerts"][0])

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("SELECT ts, score, data FROM alerts ORDER BY ts DESC LIMIT 1")
        row = c.fetchone()
        conn.close()
        if row:
            alert = json.loads(row[2])
            alert["score"] = row[1]
            alert["timestamp"] = row[0]
            return jsonify(alert)
    except Exception:
        pass

    return jsonify({"status": "error", "message": "No alerts recorded"}), 404


@app.route('/api/vision/snapshot', methods=['GET', 'POST'])
def vision_snapshot():
    if request.method == 'POST':
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No JSON body"}), 400

        snapshot_b64 = data.get("snapshot_b64")
        timestamp = data.get("timestamp", time.time())

        if not snapshot_b64:
            return jsonify({"status": "error", "message": "Missing snapshot_b64"}), 400

        system_state["vision"]["snapshot_b64"] = snapshot_b64
        system_state["vision"]["snapshot_time"] = timestamp
        system_state["vision"]["online"] = True
        system_state["vision"]["last_update"] = time.time()

        return jsonify({"status": "success", "message": "Snapshot updated"})

    # GET — return latest snapshot (no-cache to ensure dashboard always gets fresh frame)
    v = system_state["vision"]
    if not v["snapshot_b64"]:
        return jsonify({"status": "error", "message": "No snapshot available"}), 404

    resp = jsonify({
        "snapshot_b64": v["snapshot_b64"],
        "snapshot_time": v["snapshot_time"],
        "online": v["online"]
    })
    resp.headers["Cache-Control"] = "no-store"
    return resp


# --- UV Capture (SPEC-009) ---

VISION_SERVICE_URL = f"http://{SYSTEMS['main']['host']}:5050"

@app.route('/api/uv/status', methods=['GET'])
def uv_status():
    """Proxy capture status from vision service on System A."""
    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not installed"}), 503
    try:
        res = http_requests.get(f"{VISION_SERVICE_URL}/api/uv/status", timeout=2)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Vision service unreachable: {str(e)}"}), 503

@app.route('/api/uv/capture', methods=['POST'])
def uv_capture():
    """Proxy UV capture request to vision service on System A."""
    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not installed"}), 503

    try:
        duration = 2.5
        if request.json and "duration" in request.json:
            duration = request.json["duration"]

        log_activity("uv_capture", f"duration:{duration}")

        # UV cycle = ~12s warmup + capture window + return — give generous timeout
        res = http_requests.post(
            f"{VISION_SERVICE_URL}/api/uv/capture",
            json={"duration": duration},
            timeout=60
        )
        return jsonify(res.json()), res.status_code

    except Exception as e:
        return jsonify({"status": "error", "message": f"Vision service unreachable: {str(e)}"}), 503

@app.route('/api/uv/sync', methods=['POST'])
def uv_sync():
    """Proxy manual UV sync trigger to vision service on System A."""
    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not installed"}), 503
    try:
        res = http_requests.post(f"{VISION_SERVICE_URL}/api/uv/sync", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Vision service unreachable: {str(e)}"}), 503


@app.route('/api/safety/snapshot', methods=['GET'])
def safety_snapshot():
    """Proxy safety snapshot from vision service on System A."""
    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not installed"}), 503
    try:
        res = http_requests.get(f"{VISION_SERVICE_URL}/api/safety/snapshot", timeout=5)
        resp = jsonify(res.json())
        resp.headers["Cache-Control"] = "no-store"
        return resp, res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Vision service unreachable: {str(e)}"}), 503


# --- Detection Config API (SPEC-009) ---

@app.route('/api/detection/config', methods=['GET', 'POST'])
def detection_config():
    """Proxy detection config to/from vision service on System A. Admin-only for POST."""
    if not HAS_REQUESTS:
        return jsonify({"status": "error", "message": "requests library not installed"}), 503

    if request.method == 'POST':
        auth = get_auth_user()
        if not auth or auth['role'] != 'admin':
            return jsonify({"status": "error", "message": "Admin access required"}), 403
        log_activity("detection_config", json.dumps(request.json))

    try:
        if request.method == 'GET':
            res = http_requests.get(f"{VISION_SERVICE_URL}/api/detection/config", timeout=5)
        else:
            res = http_requests.post(
                f"{VISION_SERVICE_URL}/api/detection/config",
                json=request.json, timeout=5
            )
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Vision service unreachable: {str(e)}"}), 503


# --- Gateway Management API (SPEC-060) ---

@app.route('/api/gateway/status', methods=['GET'])
def gateway_wifi_status():
    """Fetch WiFi interface status from Gateway Pi (System C)."""
    # This requires bridge/onshore_bridge.py to have a /api/wifi/status endpoint
    # For now, we use a simple command proxy if available
    try:
        gw_host = "100.64.151.40"
        res = http_requests.get(f"http://{gw_host}:5001/api/wifi/status", timeout=5)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gateway unreachable: {str(e)}"}), 503

@app.route('/api/gateway/wifi', methods=['POST'])
def gateway_wifi_control():
    """Control WiFi interfaces on Gateway Pi. Admin-only."""
    auth = get_auth_user()
    if not auth or auth['role'] != 'admin':
        return jsonify({"status": "error", "message": "Admin access required"}), 403

    data = request.json
    if not data or 'interface' not in data or 'action' not in data:
        return jsonify({"status": "error", "message": "Missing interface or action"}), 400

    log_activity("gateway_wifi", f"{data['interface']} {data['action']}")

    try:
        gw_host = "100.64.151.40"
        res = http_requests.post(f"http://{gw_host}:5001/api/wifi/control", json=data, timeout=10)
        return jsonify(res.json()), res.status_code
    except Exception as e:
        return jsonify({"status": "error", "message": f"Gateway unreachable: {str(e)}"}), 503


# --- Activity Log API (SPEC-028 Section 6) ---

@app.route('/api/activity', methods=['GET'])
def get_activity():
    """Return activity log. Admin-only."""
    auth = get_auth_user()
    if not auth or auth['role'] != 'admin':
        return jsonify({"status": "error", "message": "Admin access required"}), 403

    hours = request.args.get('hours', 24, type=int)
    since = time.time() - (hours * 3600)

    try:
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute(
            "SELECT ts, ip, user, role, action, detail FROM activity_log WHERE ts > ? ORDER BY ts DESC LIMIT 500",
            (since,)
        )
        rows = c.fetchall()
        conn.close()

        entries = []
        for row in rows:
            entries.append({
                "ts": row[0],
                "ip": row[1],
                "user": row[2],
                "role": row[3],
                "action": row[4],
                "detail": row[5]
            })
        return jsonify({"status": "success", "hours": hours, "count": len(entries), "entries": entries})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# --- Public Dashboard FTP Relay ---

def ftp_telemetry_pusher():
    """Push telemetry.json to public hosting via FTP every 10s."""
    logger.info("FTP telemetry pusher started")
    while True:
        time.sleep(10)
        try:
            update_telemetry()
            # Build public-safe payload (exclude snapshot_b64 — it goes via vision FTP)
            public_state = {}
            for key in ("main", "health", "gateway", "vision"):
                section = dict(system_state[key])
                section.pop("snapshot_b64", None)
                section.pop("alerts", None)
                public_state[key] = section

            payload = json.dumps(public_state, indent=2)

            ftp = ftplib.FTP(PUBLIC_FTP_HOST, timeout=10)
            ftp.login(PUBLIC_FTP_USER, PUBLIC_FTP_PASS)
            ftp.cwd(PUBLIC_FTP_PATH)
            ftp.storbinary("STOR telemetry.json", io.BytesIO(payload.encode()))
            ftp.quit()
        except Exception as e:
            logger.warning(f"FTP telemetry push failed: {e}")


# --- Startup ---

init_local_hardware()

if __name__ == '__main__':
    threading.Thread(target=ftp_telemetry_pusher, daemon=True).start()
    app.run(host='0.0.0.0', port=5000, debug=False)
