#!/usr/bin/env python3
import time
import json
import sys
import argparse
import os
import subprocess
import threading
import base64
import re
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

try:
    import serial  # used only by --circuit P (VE.Direct)
    HAS_SERIAL = True
except ImportError:
    HAS_SERIAL = False

# Local imports
try:
    import lora_handler
    from main_bridge import MainBridge
    from health_bridge import HealthBridge
    from lora_handler import LoraHandler
    from do_sensor import DOSensor
except ImportError:
    # Fallback for parent directory execution
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import lora_handler
    from main_bridge import MainBridge
    from health_bridge import HealthBridge
    from lora_handler import LoraHandler
    from do_sensor import DOSensor

# Buoy Bridge: Unified listener for downstream LoRa commands
# Runs on BOTH Main Pi and Health Pi


# ---------------------------------------------------------------------------
# SPEC-033 — HTTP command proxy (port 5051)
# obs_center POSTs {"command": "UV:ON"|"UV:OFF"|...} to /cmd; we forward to
# the Mega over the shared serial port and return the firmware reply as JSON.
# Bound to 0.0.0.0 so it is reachable from System D over Tailscale.
# ---------------------------------------------------------------------------

PROXY_PORT = 5051
PROXY_LOCK_TIMEOUT = 4.0  # seconds — drop request rather than starve telemetry loop
serial_lock = threading.Lock()  # guards mega_bridge.connect/IO/disconnect

# ---------------------------------------------------------------------------
# Dead-serial auto-recovery (project_dead_serial_recovery_open).
# When the Pi-side cdc_acm driver enters its corrupted state, Mega reads
# return empty. After N consecutive empties we bounce the USB device.
# ---------------------------------------------------------------------------
DEAD_THRESHOLD = 3              # consecutive empty replies before recovery
RECOVERY_COOLDOWN = 120         # seconds — minimum gap between recoveries
USB_DEV_ID = os.environ.get("OP_USB_DEV_ID", "3-1")  # System A Pi 5 default
SERVICE_NAME = os.environ.get("OP_SERVICE_NAME", "buoy-bridge-main.service")
RECOVER_CMD = "/usr/local/bin/op_cdc_recover.sh"

_silent_count = 0
_silent_lock = threading.Lock()
_last_recovery_ts = 0.0


def _is_empty_reply(result):
    """Tell if a Mega result represents a 'no bytes received' state."""
    if not isinstance(result, dict):
        return True
    if result.get("status") == "success":
        return False
    msg = (result.get("message") or "").lower()
    return "no response" in msg or result.get("status") == "error"


def note_mega_response(result):
    """Bump or reset the dead-serial counter. Returns current count."""
    global _silent_count
    with _silent_lock:
        if _is_empty_reply(result):
            _silent_count += 1
        else:
            _silent_count = 0
        return _silent_count


def maybe_recover_serial():
    """If the counter is past threshold and we're outside cooldown,
    invoke the privileged recovery script. The script will stop us via
    systemd; on return we may already be killed — that is by design."""
    global _last_recovery_ts
    with _silent_lock:
        if _silent_count < DEAD_THRESHOLD:
            return False
        now = time.time()
        if now - _last_recovery_ts < RECOVERY_COOLDOWN:
            return False
        _last_recovery_ts = now
    print(f"[RECOVERY] {_silent_count} consecutive empty Mega replies — invoking {RECOVER_CMD} {USB_DEV_ID} {SERVICE_NAME}", file=sys.stderr)
    # Launch via systemd-run so the script lives in its own transient scope.
    # If we just spawned it as our child, systemd would kill it the moment the
    # script's own `systemctl stop buoy-bridge-*` killed our cgroup.
    try:
        subprocess.Popen([
            "sudo", "-n",
            "/usr/bin/systemd-run",
            "--unit=op-cdc-recover",
            "--collect",
            "--no-block",
            "--quiet",
            RECOVER_CMD, USB_DEV_ID, SERVICE_NAME,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[RECOVERY] FAILED to invoke recovery script: {e}", file=sys.stderr)
        return False
    return True


# ---------------------------------------------------------------------------
# SPEC-036 — VE.Direct text-frame parser for --circuit P (Power)
# Implements Victron VE.Direct Protocol §3 (text mode) with mod-256 checksum
# validation per FAQ Q8. Runs in a daemon thread per device, exposing
# latest_fields() to the main loop.
# ---------------------------------------------------------------------------
class VEDirectReader(threading.Thread):
    """Continuously reads a VE.Direct device, parses TEXT frames with checksum
    validation, and exposes the latest validated field dict.

    HEX-mode async messages (lines starting with ':') are skipped silently
    (FAQ Q1). Frames with bad checksums are dropped, not surfaced.
    """

    def __init__(self, port, baud=19200, label=""):
        super().__init__(daemon=True)
        self.port = port
        self.baud = baud
        self.label = label or os.path.basename(port)
        self._latest = {}
        self._latest_ts = 0.0
        self._lock = threading.Lock()
        self._ser = None
        self._stop = threading.Event()
        # Frame state
        self._buf = bytearray()
        self._checksum = 0
        self._in_hex = False

    def stop(self):
        self._stop.set()

    def latest_fields(self):
        """Return (latest_dict_copy, age_seconds). Empty dict if never received."""
        with self._lock:
            d = dict(self._latest)
            ts = self._latest_ts
        age = (time.time() - ts) if ts else float('inf')
        return d, age

    def _open(self):
        try:
            self._ser = serial.Serial(self.port, self.baud, timeout=0.5)
            return True
        except Exception as e:
            print(f"[VE.Direct:{self.label}] open failed: {e}", file=sys.stderr)
            self._ser = None
            return False

    def _close(self):
        try:
            if self._ser:
                self._ser.close()
        except Exception:
            pass
        self._ser = None

    def _process_byte(self, b):
        """Feed one byte. Frame structure: <CR><LF>K<TAB>V<CR><LF>...
        Frame ends with 'Checksum<TAB><single byte>'. The mod-256 sum of all
        bytes from the FIRST byte of the frame (the leading \\r) through the
        checksum byte itself must equal 0.

        Implementation: accumulate bytes into _buf until we recognise the
        Checksum field terminator, then validate, parse, emit, and reset.
        """
        # Handle HEX async messages — they start with ':' and end with '\n'.
        # We must NOT include them in the text checksum.
        if b == 0x3A and not self._in_hex:  # ':'
            self._in_hex = True
            return
        if self._in_hex:
            if b == 0x0A:  # '\n' ends a HEX message
                self._in_hex = False
            return

        self._buf.append(b)
        self._checksum = (self._checksum + b) & 0xFF

        # Look for the Checksum field terminator: ...\r\nChecksum\t<X>
        # The single byte after 'Checksum\t' is the checksum byte (arbitrary,
        # not printable in general). After we ingest that byte, validate.
        # We detect Checksum-line entry by scanning for b'\nChecksum\t' in the
        # tail of _buf and counting one more byte past it.
        if len(self._buf) >= 11:
            tail = bytes(self._buf[-11:])
            # Match newline + "Checksum\t" then any one byte
            if b'\nChecksum\t' in tail:
                idx = tail.rfind(b'\nChecksum\t')
                # The checksum byte position: tail[idx + len('\nChecksum\t')]
                cs_byte_pos = idx + 10  # 10 = len('\nChecksum\t')
                if cs_byte_pos == len(tail) - 1:
                    # We just consumed the checksum byte. Validate.
                    self._validate_and_emit()
                    self._buf.clear()
                    self._checksum = 0

    def _validate_and_emit(self):
        if (self._checksum & 0xFF) != 0:
            # Bad checksum — drop the frame.
            return
        # Parse fields from _buf (excluding leading \r\n and trailing Checksum line).
        try:
            text = bytes(self._buf).decode('ascii', errors='replace')
        except Exception:
            return
        fields = {}
        # Each record is on its own line as KEY<TAB>VALUE.
        for line in text.split('\r\n'):
            line = line.strip('\r\n')
            if not line or line.startswith('Checksum'):
                continue
            if '\t' not in line:
                continue
            k, _, v = line.partition('\t')
            k = k.strip()
            v = v.strip()
            if k:
                fields[k] = v
        if fields:
            with self._lock:
                # Merge (not replace): SmartShunt emits two interleaved frame
                # types per cycle (H1..H18 stats, then PID/V/I/P/SOC live). If
                # we replaced, half the cycles would land with the wrong subset
                # in _latest and the packer would emit incomplete P:STATUS.
                self._latest.update(fields)
                self._latest_ts = time.time()

    def run(self):
        backoff = 1.0
        while not self._stop.is_set():
            if not self._ser and not self._open():
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 30.0)
                continue
            backoff = 1.0
            try:
                chunk = self._ser.read(256)
            except Exception as e:
                print(f"[VE.Direct:{self.label}] read error: {e}", file=sys.stderr)
                self._close()
                continue
            if not chunk:
                continue
            for b in chunk:
                self._process_byte(b)
        self._close()


# ---------------------------------------------------------------------------
# SPEC-036 — pack MPPT + Shunt fields into the compact P:STATUS payload
# ---------------------------------------------------------------------------
def _safe_int(v, default=None):
    try:
        return int(float(v))
    except (TypeError, ValueError):
        return default

def build_power_payload(mppt_fields, shunt_fields):
    """Return a P:STATUS=... payload string per SPEC-036 §3.2, or None if no
    usable data from either device."""
    parts = []

    def add(key, fn_field, fields):
        # fn_field is (raw_key, scaler) — scaler turns the raw VE.Direct
        # value into the compact integer required by the packet schema.
        raw_key, scaler = fn_field
        if raw_key not in fields:
            return
        v_raw = fields.get(raw_key)
        v = scaler(v_raw)
        if v is None:
            return
        parts.append(f"{key}={v}")

    # MPPT fields — VE.Direct units: V/I in mV/mA, P in W, VPV mV, PPV W.
    # Encoded as: V centivolts (V/10), I centi-amps (I/10), VPV decivolts (V/100),
    # PPV watts int, IL centi-amps, CS int, ERR int.
    add("PV", ("VPV", lambda v: _safe_int(int(v) / 100) if v.lstrip("-").isdigit() else None), mppt_fields)
    add("PW", ("PPV", _safe_int), mppt_fields)
    add("CI", ("I",   lambda v: _safe_int(int(v) / 10)  if v.lstrip("-").isdigit() else None), mppt_fields)
    add("LI", ("IL",  lambda v: _safe_int(int(v) / 10)  if v.lstrip("-").isdigit() else None), mppt_fields)
    add("CS", ("CS",  _safe_int), mppt_fields)
    add("ER", ("ERR", _safe_int), mppt_fields)

    # Shunt fields — VE.Direct units: V mV, I mA, P W, SOC per-mille.
    # Encoded: SV centivolts (V/10), SI centi-amps (I/10), SP watts int,
    # SOC per-mille int (already in tenths-of-percent from VE.Direct).
    add("SV",  ("V",   lambda v: _safe_int(int(v) / 10) if v.lstrip("-").isdigit() else None), shunt_fields)
    add("SI",  ("I",   lambda v: _safe_int(int(v) / 10) if v.lstrip("-").isdigit() else None), shunt_fields)
    add("SP",  ("P",   _safe_int), shunt_fields)
    add("SOC", ("SOC", _safe_int), shunt_fields)

    if not parts:
        return None
    return "P:STATUS=" + ",".join(parts)


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


do_lock = threading.Lock()  # SPEC-034: guards DOSensor access between poll loop and proxy

def _handle_do_command(do_sensor, cmd):
    """Handle DO:* commands forwarded via the bridge command proxy.

    Supported (case-insensitive):
        DO:READ                       — read DO sat/mgL/water_temp
        DO:CAL:SAT                    — write 0x0002 to 0x1010 (100% sat calibration)
        DO:CAL:ZERO                   — write 0x0001 to 0x1010 (zero-point calibration)
        DO:SAL:GET                    — read salinity setting register 0x1020
        DO:SAL:SET:<n>                — write salinity (0..255 ‰)
        DO:PRESS:GET                  — read atmospheric pressure register 0x1022 (×100)
        DO:PRESS:SET:<n>              — write pressure ×100 (e.g. 10133 = 101.33 kPa)
        DO:ADDR:GET                   — read configured Modbus address
        DO:BAUD:GET                   — read configured baud-rate index

    Returns a dict suitable for JSON reply.
    """
    if do_sensor is None:
        return {"status": "error", "message": "DO sensor not present on this circuit"}
    parts = cmd.upper().split(":")
    if len(parts) < 2 or parts[0] != "DO":
        return {"status": "error", "message": f"bad DO command: {cmd}"}
    op = parts[1]
    with do_lock:
        try:
            if op == "READ":
                d = do_sensor.read_all()
                return {"status": "success" if d else "error", "data": d}
            if op == "CAL" and len(parts) == 3:
                sub = parts[2]
                if sub == "SAT":
                    ok = do_sensor.calibrate_saturation()
                    return {"status": "success" if ok else "error", "reg": "0x1010", "wrote": "0x0002"}
                if sub == "ZERO":
                    ok = do_sensor.calibrate_zero()
                    return {"status": "success" if ok else "error", "reg": "0x1010", "wrote": "0x0001"}
                return {"status": "error", "message": f"unknown CAL subcmd: {sub}"}
            if op == "SAL":
                if len(parts) == 3 and parts[2] == "GET":
                    v = do_sensor.get_salinity_ppt()
                    return {"status": "success" if v is not None else "error", "salinity_ppt": v}
                if len(parts) == 4 and parts[2] == "SET":
                    try: n = int(parts[3])
                    except ValueError: return {"status": "error", "message": "bad int"}
                    ok = do_sensor.set_salinity_ppt(n)
                    return {"status": "success" if ok else "error", "salinity_ppt": n}
            if op == "PRESS":
                if len(parts) == 3 and parts[2] == "GET":
                    v = do_sensor.get_pressure_kpa_x100()
                    return {"status": "success" if v is not None else "error", "pressure_x100": v}
                if len(parts) == 4 and parts[2] == "SET":
                    try: n = int(parts[3])
                    except ValueError: return {"status": "error", "message": "bad int"}
                    ok = do_sensor.set_pressure_kpa_x100(n)
                    return {"status": "success" if ok else "error", "pressure_x100": n}
            if op == "ADDR" and len(parts) == 3 and parts[2] == "GET":
                v = do_sensor.get_addr()
                return {"status": "success" if v is not None else "error", "addr": v}
            if op == "BAUD" and len(parts) == 3 and parts[2] == "GET":
                v = do_sensor.get_baud_index()
                return {"status": "success" if v is not None else "error", "baud_index": v}
            return {"status": "error", "message": f"unknown DO command: {cmd}"}
        except Exception as e:
            return {"status": "error", "message": f"DO exception: {e}"}


def make_proxy_handler(mega_bridge, do_sensor=None):
    class ProxyHandler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):  # silence default access log
            return

        def _reply(self, code, payload):
            try:
                body = json.dumps(payload).encode("utf-8")
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                # Client gave up before we replied — nothing to do, don't pollute the log
                pass

        def do_POST(self):
            if self.path != "/cmd":
                return self._reply(404, {"status": "error", "message": "not found"})
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw = self.rfile.read(length) if length else b""
                data = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception as e:
                return self._reply(400, {"status": "error", "message": f"bad json: {e}"})

            cmd = (data.get("command") or "").strip()
            if not cmd:
                return self._reply(400, {"status": "error", "message": "missing 'command'"})

            # SPEC-034: DO:* commands talk to the optical DO sensor via Modbus
            # (separate serial port from the Mega), guarded by do_lock. Mega
            # serial_lock is not used here — paths are independent.
            if cmd.upper().startswith("DO:"):
                result = _handle_do_command(do_sensor, cmd)
                return self._reply(200, result)

            if not serial_lock.acquire(timeout=PROXY_LOCK_TIMEOUT):
                return self._reply(503, {"status": "error", "message": "serial busy, try again"})
            try:
                if not mega_bridge.connect():
                    return self._reply(502, {"status": "error", "message": "serial connect failed"})
                try:
                    result = mega_bridge._send_command(cmd)
                finally:
                    mega_bridge.disconnect()
            finally:
                serial_lock.release()
            note_mega_response(result)
            maybe_recover_serial()
            return self._reply(200, result)

        def do_GET(self):
            if self.path == "/health":
                return self._reply(200, {"status": "ok"})
            return self._reply(404, {"status": "error", "message": "not found"})

    return ProxyHandler


def start_command_proxy(mega_bridge, do_sensor=None):
    server = ThreadedHTTPServer(("0.0.0.0", PROXY_PORT), make_proxy_handler(mega_bridge, do_sensor))
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()
    print(f"Command proxy listening on 0.0.0.0:{PROXY_PORT} (threaded)")
    return server


def main():
    parser = argparse.ArgumentParser(description="OceanPulse Buoy LoRa Bridge")
    parser.add_argument("--circuit", required=True, choices=['M', 'H', 'P'], help="Circuit ID (M=Main, H=Health, P=Power)")
    parser.add_argument("--lora-port", default='/dev/ttyUSB0', help="LoRa Serial Port")
    parser.add_argument("--mega-port", default='/dev/ttyACM0', help="Arduino Mega Serial Port")
    # SPEC-036 Power circuit ports + cadence
    parser.add_argument("--mppt-port", default='/dev/op-vedirect', help="MPPT VE.Direct port (circuit P)")
    parser.add_argument("--shunt-port", default='/dev/op-shunt', help="SmartShunt VE.Direct port (circuit P)")
    parser.add_argument("--interval", type=int, default=30, help="Telemetry cadence in seconds (default 30 for circuit P, 30 for others)")
    args = parser.parse_args()

    circuit_id = args.circuit
    print(f"Starting Buoy LoRa Bridge for Circuit {circuit_id}")

    # SPEC-036: Power circuit takes a dedicated path — VE.Direct readers + LoRa,
    # no Mega bridge.
    if circuit_id == 'P':
        if not HAS_SERIAL:
            print("FATAL: pyserial is required for --circuit P", file=sys.stderr)
            sys.exit(1)
        lora = LoraHandler(port=args.lora_port, mode='AT')
        mppt_reader = VEDirectReader(args.mppt_port, label="mppt")
        shunt_reader = VEDirectReader(args.shunt_port, label="shunt")
        mppt_reader.start()
        shunt_reader.start()
        print(f"VE.Direct readers started: MPPT={args.mppt_port} SHUNT={args.shunt_port}")
        if not lora.connect():
            print("FATAL: LoRa connect failed", file=sys.stderr)
            sys.exit(1)
        print(f"LoRa Connected (Power circuit). Cadence={args.interval}s")
        try:
            # Allow first frames to arrive before sending the first packet.
            time.sleep(min(args.interval, 5))
            while True:
                mppt_fields, mppt_age = mppt_reader.latest_fields()
                shunt_fields, shunt_age = shunt_reader.latest_fields()
                # Stale-data guard: drop a side that hasn't been heard from in 3
                # consecutive cycles.
                STALE_S = max(args.interval * 3, 15)
                if mppt_age > STALE_S:
                    mppt_fields = {}
                if shunt_age > STALE_S:
                    shunt_fields = {}
                payload = build_power_payload(mppt_fields, shunt_fields)
                if payload:
                    with serial_lock:
                        try:
                            lora.send_text(payload)
                        except Exception as e:
                            print(f"LoRa TX failed: {e}", file=sys.stderr)
                    print(f"TX {payload} (mppt_age={mppt_age:.1f}s shunt_age={shunt_age:.1f}s)")
                else:
                    print(f"No usable VE.Direct data (mppt_age={mppt_age:.1f}s shunt_age={shunt_age:.1f}s) — skipping packet")
                time.sleep(args.interval)
        except KeyboardInterrupt:
            print("Stopping Power circuit...")
        finally:
            mppt_reader.stop()
            shunt_reader.stop()
            lora.close()
        return

    # Initialize local hardware bridge (M/H paths)
    if circuit_id == 'M':
        mega_bridge = MainBridge(port=args.mega_port)
        do_sensor = DOSensor() # Default /dev/ttyUSB1
    else:
        mega_bridge = HealthBridge(port=args.mega_port)
        do_sensor = None

    # SPEC-036: on Health circuit, ALSO read VE.Direct devices and emit P:STATUS
    # in the same loop. A separate --circuit P process would conflict over
    # /dev/op-lora (serial_lock is process-local); single-process ownership is
    # the only race-free pattern.
    power_readers_enabled = (
        circuit_id == 'H'
        and HAS_SERIAL
        and os.path.exists(args.mppt_port)
        and os.path.exists(args.shunt_port)
    )
    mppt_reader = None
    shunt_reader = None
    if power_readers_enabled:
        try:
            mppt_reader = VEDirectReader(args.mppt_port, label="mppt")
            shunt_reader = VEDirectReader(args.shunt_port, label="shunt")
            mppt_reader.start()
            shunt_reader.start()
            print(f"VE.Direct power readers started: MPPT={args.mppt_port} SHUNT={args.shunt_port}")
        except Exception as e:
            print(f"WARN: VE.Direct readers failed to start: {e}", file=sys.stderr)
            mppt_reader = None
            shunt_reader = None

    lora = LoraHandler(port=args.lora_port, mode='AT')

    # SPEC-033: only the Main circuit exposes the HTTP command proxy (UV is on Main).
    if circuit_id == 'M':
        try:
            start_command_proxy(mega_bridge, do_sensor)
        except Exception as e:
            print(f"WARN: command proxy failed to start: {e}", file=sys.stderr)

    def on_lora_message(payload):
        # Format: C:<TARGET_ID>:<CMD>[:<PARAM>]
        parts = payload.split(':')
        if len(parts) < 3 or parts[0] != 'C':
            return

        target_id = parts[1]
        cmd = parts[2]

        # Check if message is for THIS circuit
        if target_id != circuit_id and target_id != 'B':
            return

        print(f"Executing LoRa Command: {cmd}")

        if cmd == "REBOOT":
            # Cross-circuit reset logic
            with serial_lock:
                if mega_bridge.connect():
                    res = mega_bridge.reboot()
                    print(f"Reset Result: {res}")
                    mega_bridge.disconnect()

        elif cmd == "SOFT_REBOOT":
            # SPEC-025: Pi-level soft reboot via LoRa
            print("SOFT REBOOT command received via LoRa")
            try:
                lora.send_text(f"{circuit_id}:SOFT_REBOOT:ACK")
            except Exception as e:
                print(f"WARN: SOFT_REBOOT ACK send failed: {e}", file=sys.stderr)
            time.sleep(1)
            subprocess.run(["sudo", "reboot"])

        elif cmd == "RELAY":
            # Direct relay control via LoRa
            if len(parts) >= 4 and parts[3] in ("ON", "OFF"):
                state = parts[3] == "ON"
                with serial_lock:
                    if mega_bridge.connect():
                        res = mega_bridge.set_relay(state)
                        print(f"Relay Result: {res}")
                        mega_bridge.disconnect()

        elif cmd == "UV":
            # SPEC-033: UV pin toggle via LoRa (downstream path; HTTP proxy is the primary)
            if len(parts) >= 4 and parts[3] in ("ON", "OFF"):
                with serial_lock:
                    if mega_bridge.connect():
                        res = mega_bridge._send_command(f"UV:{parts[3]}")
                        print(f"UV Result: {res}")
                        mega_bridge.disconnect()

        elif cmd == "SAFETY":
            # SPEC-035: UV hardware safety interlock config via LoRa
            if len(parts) >= 4:
                # Reconstruct subcommand from parts[3:] (e.g. HEAT:ON or DIST_THR:150)
                subcmd = ":".join(parts[3:])
                with serial_lock:
                    if mega_bridge.connect():
                        res = mega_bridge._send_command(f"SAFETY:{subcmd}")
                        print(f"SAFETY Result: {res}")
                        mega_bridge.disconnect()

        elif cmd == "SHELL":
            # SPEC-026: LoRa Remote Shell (Emergency Recovery)
            # Format: C:<TARGET>:SHELL:<CMD_ID>:<BASE64_COMMAND>
            if len(parts) >= 5:
                cmd_id = parts[3]
                b64_cmd = parts[4]
                try:
                    raw_cmd = base64.b64decode(b64_cmd).decode('utf-8').strip()
                except Exception as e:
                    print(f"SHELL: B64 decode failed: {e}")
                    return

                # Whitelist enforcement
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
                
                authorized = any(re.match(pattern, raw_cmd) for pattern in WHITELIST)
                if not authorized:
                    print(f"SHELL: BLOCKED unauthorized command: {raw_cmd}")
                    err_b64 = base64.b64encode(b'ERR_WHITELIST').decode()
                    lora.send_text(f"{circuit_id}:SHELL:ACK:{cmd_id}:0:1:{err_b64}")
                    return

                print(f"SHELL: Executing: {raw_cmd}")
                try:
                    res = subprocess.run(raw_cmd, shell=True, capture_output=True, text=True, timeout=5)
                    output = (res.stdout + res.stderr).strip()
                    if not output:
                        output = f"Done (exit {res.returncode})"
                except subprocess.TimeoutExpired:
                    output = "ERR_TIMEOUT"
                except Exception as e:
                    output = f"ERR_EXEC:{str(e)}"

                # Chunking (max 40 bytes per chunk to stay safe under LoRa SF12 limit)
                # Packet format: <TARGET>:SHELL:ACK:<CMD_ID>:<CHUNK_IDX>:<TOTAL_CHUNKS>:<BASE64_DATA>
                out_bytes = output.encode('utf-8')[:200] # Cap at 200 bytes per SPEC
                chunk_size = 30 # Small chunks for reliability
                total_chunks = (len(out_bytes) + chunk_size - 1) // chunk_size
                if total_chunks == 0: total_chunks = 1

                for i in range(total_chunks):
                    chunk = out_bytes[i*chunk_size : (i+1)*chunk_size]
                    b64_data = base64.b64encode(chunk).decode()
                    lora.send_text(f"{circuit_id}:SHELL:ACK:{cmd_id}:{i}:{total_chunks}:{b64_data}")
                    time.sleep(0.5) # Gap between chunks

        elif cmd == "PING":
            # Upstream ACK
            lora.send_text(f"{circuit_id}:PONG")

    if lora.connect():
        print("LoRa Connected. Listening for commands and reporting telemetry...")

        # We use a thread for listening so the main loop can handle periodic telemetry
        listen_thread = threading.Thread(target=lora.listen, kwargs={'callback': on_lora_message}, daemon=True)
        listen_thread.start()

        try:
            while True:
                # 1. Collect Full Status Telemetry
                res = {"status": "error", "message": "no connect"}
                with serial_lock:
                    if mega_bridge.connect():
                        res = mega_bridge.get_status()
                        if res.get("status") == "success":
                            # LoRa SF12/BW125 caps useful payload around ~80 bytes.
                            # Drop fields not used by the dashboard, alias Health keys
                            # to short forms, and round DHT11 to integer (its own
                            # resolution is 1°C/1%RH anyway). onshore_bridge expands
                            # the aliases back to long names.
                            # BATT dropped from H:STATUS LoRa TX (REQ-055 follow-up + payload
                            # budget after DHT4 added). Real battery voltage lives in Power
                            # card via SmartShunt; the Mega's BATT reading from A1 is the
                            # legacy fake/duplicate. Saves ~8 bytes per H packet, keeps us
                            # under the ~80-byte SF12/BW125 ceiling.
                            DROP_KEYS = {"TDS", "RELAY", "WD", "BATT"}
                            SHORT_KEYS = {
                                "SHT_T": "ST", "SHT_H": "SH",
                                "DHT1_T": "T1", "DHT1_H": "H1",
                                "DHT2_T": "T2", "DHT2_H": "H2",
                                "DHT3_T": "T3", "DHT3_H": "H3",
                                "DHT4_T": "T4", "DHT4_H": "H4",
                                "BATT": "B",
                            }
                            INT_KEYS = {"DHT1_T", "DHT1_H", "DHT2_T", "DHT2_H",
                                        "DHT3_T", "DHT3_H", "DHT4_T", "DHT4_H"}

                            def _fmt(k, v):
                                ku = k.upper()
                                if ku in INT_KEYS:
                                    try: v = int(float(v))
                                    except: pass
                                return f"{SHORT_KEYS.get(ku, ku)}={v}"

                            # Normalise to (key, value) pairs from whichever path
                            # the Mega bridge took: parsed dict or raw value string
                            # (a comma-separated "K=V,K=V,..." emitted by firmware).
                            if "data" in res:
                                kv_pairs = list(res["data"].items())
                            else:
                                kv_pairs = []
                                for token in (res.get("value") or "").split(","):
                                    if "=" in token:
                                        k, _, v = token.partition("=")
                                        kv_pairs.append((k.strip(),
                                                          v.strip().rstrip("V").rstrip("C").rstrip("%").replace("ppm", "")))
                            parts = [_fmt(k, v) for k, v in kv_pairs
                                     if k.upper() not in DROP_KEYS]
                            clean_status = ",".join(parts)

                            if do_sensor:
                                try:
                                    with do_lock:
                                        do_data = do_sensor.read_all()
                                    if do_data:
                                        # Transmit raw saturation% and water temp.
                                        # obs_center derives mg/L using measured (or
                                        # configured) salinity via Garcia-Gordon. The
                                        # sensor's own mg/L assumes a fixed salinity
                                        # baked into register 0x1020, which is wrong
                                        # whenever real salinity differs.
                                        clean_status += f",SAT={do_data['do_sat']:.1f},WTEMP={do_data['water_temp']:.1f}"
                                except Exception as e:
                                    print(f"DO poll failed: {e}")
                            
                            lora.send_text(f"{circuit_id}:STATUS={clean_status}")
                        mega_bridge.disconnect()

                note_mega_response(res)
                maybe_recover_serial()

                # SPEC-036: emit P:STATUS in the same loop iteration (Health
                # circuit only — Main has no VE.Direct devices). Same LoRa
                # radio, same process, no inter-process serial races.
                if mppt_reader and shunt_reader:
                    try:
                        mppt_fields, mppt_age = mppt_reader.latest_fields()
                        shunt_fields, shunt_age = shunt_reader.latest_fields()
                        STALE_S = 90
                        if mppt_age > STALE_S:
                            mppt_fields = {}
                        if shunt_age > STALE_S:
                            shunt_fields = {}
                        payload = build_power_payload(mppt_fields, shunt_fields)
                        if payload:
                            with serial_lock:
                                try:
                                    lora.send_text(payload)
                                    print(f"TX {payload} (mppt_age={mppt_age:.1f}s shunt_age={shunt_age:.1f}s)")
                                except Exception as e:
                                    print(f"P: TX failed: {e}", file=sys.stderr)
                    except Exception as e:
                        print(f"P: build/TX exception: {e}", file=sys.stderr)

                # 2. Wait for next cycle
                time.sleep(30)  # Report every 30 seconds
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            lora.close()


if __name__ == "__main__":
    main()
