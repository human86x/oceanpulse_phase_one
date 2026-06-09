import cv2
import time
import json
import base64
import io
import ftplib
import subprocess
import re
import threading
import numpy as np
import urllib.request
import requests
from flask import Flask, Response, jsonify, request

app = Flask(__name__)

# CONFIGURATION
CONFIG_FILE = "config.json"
DEFAULT_CONFIG = {
    "device_index": 0,
    "width": 640,
    "height": 480,
    "api_endpoint": "http://100.77.91.123:5000/api/vision/alert",
    "public_ftp_host": None,
    "public_ftp_user": None,
    "public_ftp_pass": None,
    "public_ftp_path": "public_html/dashboard"
}

try:
    with open(CONFIG_FILE, 'r') as f:
        config = json.load(f)
except:
    config = DEFAULT_CONFIG

# SHARED STATE
camera = None
camera_lock = threading.Lock()

# Detection tuning parameters (adjustable via API)
DETECTION_CONFIG = {
    "brightness_thresh": 80,    # 0-255: min brightness for fluorescence
    "saturation_thresh": 50,    # 0-255: min saturation (color vs reflection)
    "min_region_px": 50,        # min contour area in pixels
    "score_scale": 2000,        # coverage multiplier (2000 = 5% coverage -> score 100)
    "morph_kernel": 5,          # morphology kernel size for noise cleanup
    "uv_warmup": 10.0,          # seconds to wait after UV ON (standard mode)
    "capture_samples": 6,       # frames to sample during capture
    "capture_window": 3.0,      # seconds over which to sample frames
    "auto_detect": True,        # Watch for brightness jump (the flash)
    "trigger_factor": 1.2,      # Lowered: Trigger if 20% brighter than baseline
    "flash_max_wait": 25.0,     # Increased wait time for slow relays
    "sampler_enabled": False,   # Night Hunter background thread
    "sampler_start_hour": 22,   # 24h format (10 PM)
    "sampler_end_hour": 6,      # 24h format (6 AM)
    "sampler_interval_min": 30  # Minutes between samples
}

# Serial commands are routed through buoy_bridge's HTTP proxy
# to avoid dual-access contention on /dev/op-mega
BRIDGE_CMD_URL = "http://127.0.0.1:5051/cmd"


def init_camera():
    device = config.get("device_index", 0)
    print(f"[VISION] Opening camera {device}...")
    cam = cv2.VideoCapture(device, cv2.CAP_V4L2)
    if not cam.isOpened():
        print(f"[VISION] WARN: Camera {device} failed. Trying 1...")
        cam = cv2.VideoCapture(1, cv2.CAP_V4L2)
    if cam.isOpened():
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, config["width"])
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, config["height"])
        # Set buffer size small for real-time flash detection
        cam.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        print(f"[VISION] Camera ready: {int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))}x{int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
    else:
        print("[VISION] FATAL: No camera available")
        cam = None
    return cam


def usb_recover_camera():
    """Attempt USB reset to recover dead camera."""
    print("[VISION] Attempting USB camera recovery...")
    try:
        lsusb = subprocess.run(["lsusb"], capture_output=True, text=True, timeout=5)
        for line in lsusb.stdout.splitlines():
            if "0c45:" in line or "Arducam" in line or "Webcam" in line or "Camera" in line:
                m = re.match(r'Bus (\d+) Device (\d+)', line)
                if m:
                    busdev = f"{m.group(1)}/{m.group(2)}"
                    print(f"[VISION] usbreset {busdev}")
                    r = subprocess.run(["sudo", "usbreset", busdev],
                                      capture_output=True, text=True, timeout=10)
                    print(f"[VISION] usbreset: {r.stdout.strip()} {r.stderr.strip()}")
                    return True
    except Exception as e:
        print(f"[VISION] USB recovery failed: {e}")
    return False


def grab_frame(retries=3):
    """Grab a single fresh frame from camera. Handles recovery."""
    global camera
    with camera_lock:
        for attempt in range(retries):
            if not camera or not camera.isOpened():
                camera = init_camera()
                if not camera:
                    usb_recover_camera()
                    time.sleep(3)
                    camera = init_camera()
                if not camera:
                    return None

            # Flush stale buffered frames
            for _ in range(3):
                camera.read()
            success, frame = camera.read()
            if success:
                frame = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
                return frame
            else:
                print(f"[VISION] Frame read failed (attempt {attempt+1}/{retries})")
                camera.release()
                usb_recover_camera()
                time.sleep(3)
                camera = init_camera()
    return None


def send_mega_command(cmd, retries=3):
    """Send a command to the Arduino Mega via buoy_bridge's HTTP proxy.
    This eliminates serial port contention — only the bridge touches /dev/op-mega."""
    for attempt in range(retries):
        try:
            payload = json.dumps({"command": cmd}).encode()
            req = urllib.request.Request(
                BRIDGE_CMD_URL,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                result = json.loads(resp.read().decode())
                # Extract the raw response value for callers that expect a string
                if result.get("status") == "success":
                    value = result.get("value", "")
                    raw = f"{cmd.split(':')[0]}:OK:{value}" if value else f"{cmd.split(':')[0]}:OK"
                    print(f"[UV] Mega cmd '{cmd}' -> '{raw}'")
                    return raw
                else:
                    raw = result.get("message", "")
                    print(f"[UV] Mega cmd '{cmd}' -> error: {raw}")
                    return raw
        except urllib.error.URLError as e:
            print(f"[UV] Bridge proxy attempt {attempt+1}/{retries} failed: {e}")
            time.sleep(1)
        except Exception as e:
            print(f"[UV] Unexpected error: {e}")
            time.sleep(1)
    return None


def ftp_upload_snapshot(jpeg_bytes, timestamp):
    """Upload snapshot JPEG + metadata to public hosting via FTP."""
    ftp_host = config.get("public_ftp_host")
    if not ftp_host:
        return

    ftp_user = config.get("public_ftp_user", "")
    ftp_pass = config.get("public_ftp_pass", "")
    ftp_path = config.get("public_ftp_path", "public_html/dashboard")

    try:
        ftp = ftplib.FTP(ftp_host, timeout=10)
        ftp.login(ftp_user, ftp_pass)
        ftp.cwd(ftp_path)
        ftp.storbinary("STOR snapshot.jpg", io.BytesIO(jpeg_bytes))
        meta = json.dumps({"timestamp": timestamp, "size": len(jpeg_bytes)})
        ftp.storbinary("STOR snapshot_meta.json", io.BytesIO(meta.encode()))
        ftp.quit()
        print(f"[VISION] Snapshot uploaded via FTP ({len(jpeg_bytes)} bytes)")
    except Exception as e:
        print(f"[VISION] FTP upload FAILED: {str(e)}")


def analyze_fluorescence(frame):
    """Analyze a UV-lit frame for oil fluorescence.
    Oil fluoresces as bright spots (yellow-green/blue-white) against dark background.
    Returns score 0-100 and region count."""

    dc = DETECTION_CONFIG

    # Convert to HSV — fluorescence shows as high brightness/saturation spots
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    # Threshold for bright regions (fluorescence stands out in dark UV scene)
    _, bright_mask = cv2.threshold(gray, dc["brightness_thresh"], 255, cv2.THRESH_BINARY)

    # Also look for saturated color (fluorescence has color, reflections don't)
    saturation = hsv[:, :, 1]
    _, sat_mask = cv2.threshold(saturation, dc["saturation_thresh"], 255, cv2.THRESH_BINARY)

    # Combine: bright AND saturated = likely fluorescence
    fluor_mask = cv2.bitwise_and(bright_mask, sat_mask)

    # Clean up noise
    ks = dc["morph_kernel"]
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (ks, ks))
    fluor_mask = cv2.morphologyEx(fluor_mask, cv2.MORPH_OPEN, kernel)
    fluor_mask = cv2.morphologyEx(fluor_mask, cv2.MORPH_CLOSE, kernel)

    # Find contours (fluorescent regions)
    contours, _ = cv2.findContours(fluor_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    # Filter small noise
    significant = [c for c in contours if cv2.contourArea(c) > dc["min_region_px"]]

    # Calculate score: percentage of frame that's fluorescent
    total_pixels = frame.shape[0] * frame.shape[1]
    fluor_pixels = cv2.countNonZero(fluor_mask)
    coverage = fluor_pixels / total_pixels

    # Score: 0-100, scaled by configurable factor
    score = min(100, int(coverage * dc["score_scale"]))

    mean_brightness = float(gray.mean())

    # Draw red contours around fluorescent regions on the frame
    for c in significant:
        cv2.drawContours(frame, [c], -1, (0, 0, 255), 2)
        x, y, w, h = cv2.boundingRect(c)
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 0, 255), 1)

    result = {
        "score": score,
        "regions": len(significant),
        "coverage_pct": round(coverage * 100, 2),
        "mean_brightness": round(mean_brightness, 1),
        "fluor_pixels": int(fluor_pixels)
    }
    print(f"[UV] Analysis: score={score}, regions={len(significant)}, coverage={coverage*100:.2f}%, brightness={mean_brightness:.1f}")
    return result


# UV Capture lock — prevent concurrent captures
# Capture state for real-time dashboard progress (SPEC-061)
CAPTURE_STATUS = {
    "active": False,
    "stage": "IDLE",     # IDLE, WARMUP, HARDWARE_DELAY, BURST, ANALYSIS
    "progress": 0,       # 0-100
    "time_left": 0,
    "last_max_brightness": 0.0,
    "wait_started_at": None,    # epoch ts when HARDWARE_DELAY entered
    "burst_started_at": None,   # epoch ts when BURST entered
    "manual_sync_at": None      # {"stage","delta_s","ts"} on user mark, else None
}

uv_lock = threading.Lock()
sync_event = threading.Event()


@app.route('/api/uv/status', methods=['GET'])
def get_uv_status():
    """Return current UV capture progress."""
    return jsonify(CAPTURE_STATUS)


@app.route('/api/uv/sync', methods=['POST'])
def uv_sync():
    """Manual flash mark. During HARDWARE_DELAY also short-circuits the wait."""
    if not CAPTURE_STATUS["active"]:
        return jsonify({"status": "error", "message": "No capture in progress"}), 400
    stage = CAPTURE_STATUS["stage"]
    now = time.time()
    if stage == "HARDWARE_DELAY":
        t0 = CAPTURE_STATUS.get("wait_started_at") or now
        delta = round(now - t0, 2)
        CAPTURE_STATUS["manual_sync_at"] = {"stage": stage, "delta_s": delta, "ts": now}
        sync_event.set()
        print(f"[UV] MANUAL SYNC at T+{delta}s of HARDWARE_DELAY (short-circuiting wait)")
        return jsonify({"status": "success", "stage": stage, "delta_s": delta,
                        "message": f"Marked at T+{delta}s of HARDWARE_DELAY (jumping to burst)"})
    if stage == "BURST":
        t0 = CAPTURE_STATUS.get("burst_started_at") or now
        delta = round(now - t0, 2)
        CAPTURE_STATUS["manual_sync_at"] = {"stage": stage, "delta_s": delta, "ts": now}
        print(f"[UV] MANUAL FLASH MARK at T+{delta}s of BURST")
        return jsonify({"status": "success", "stage": stage, "delta_s": delta,
                        "message": f"Marked at T+{delta}s of BURST"})
    return jsonify({"status": "error", "message": f"Cannot mark during stage {stage}"}), 400


@app.route('/api/uv/capture', methods=['POST'])
def uv_capture():
    """UV Capture sequence: UV ON -> warmup/detect -> capture frames -> UV OFF -> return image."""
    if not uv_lock.acquire(blocking=False):
        return jsonify({"status": "error", "message": "UV capture already in progress"}), 409

    # Reset status and event
    CAPTURE_STATUS["active"] = True
    CAPTURE_STATUS["stage"] = "WARMUP"
    CAPTURE_STATUS["progress"] = 0
    CAPTURE_STATUS["time_left"] = 20
    CAPTURE_STATUS["wait_started_at"] = None
    CAPTURE_STATUS["burst_started_at"] = None
    CAPTURE_STATUS["manual_sync_at"] = None
    sync_event.clear()

    try:
        # 1. Turn UV ON
        resp = send_mega_command("UV:ON")
        if resp is None:
            CAPTURE_STATUS["active"] = False
            uv_lock.release()
            return jsonify({"status": "error", "message": "Failed to send UV:ON — serial port unavailable"}), 503

        best_frame = None
        best_brightness = -1
        samples = DETECTION_CONFIG["capture_samples"]
        
        if DETECTION_CONFIG.get("auto_detect"):
            print("[UV] High-speed Blind Burst active. Waiting for hardware delay (11.5s) or Manual Sync...")
            warmup = 0.0
            
            # 2a. Watch during the 11.5s wait too, just in case flash happens early
            CAPTURE_STATUS["stage"] = "HARDWARE_DELAY"
            start_wait = time.time()
            CAPTURE_STATUS["wait_started_at"] = start_wait
            while (time.time() - start_wait) < 11.5:
                # Check for Manual Sync Event
                if sync_event.is_set():
                    print("[UV] MANUAL SYNC RECEIVED! Jumping to burst...")
                    break

                CAPTURE_STATUS["progress"] = int((time.time() - start_wait) * 4.3) # 0 to 50% approx
                CAPTURE_STATUS["time_left"] = int(15 - (time.time() - start_wait))
                
                # Check for premature flash
                frame = grab_frame(retries=0)
                if frame is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    b = float(gray.mean())
                    if b > 15.0: # If we see light during wait, jump to burst immediately
                        print(f"[UV] Early light detected ({b:.1f})! Entering burst...")
                        break
                time.sleep(0.1) # Faster poll for sync event
            
            print("[UV] Starting 3.5-second capture burst (targeting 2s flash)...")
            CAPTURE_STATUS["stage"] = "BURST"
            start_burst = time.time()
            CAPTURE_STATUS["burst_started_at"] = start_burst
            burst_frames = []
            
            while (time.time() - start_burst) < 3.5:
                # Progress from 50 to 95%
                CAPTURE_STATUS["progress"] = 50 + int((time.time() - start_burst) * 12.8)
                CAPTURE_STATUS["time_left"] = int(3.5 - (time.time() - start_burst))

                frame = grab_frame(retries=1)
                if frame is not None:
                    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                    b = float(gray.mean())
                    burst_frames.append((b, frame))
                    if b > best_brightness:
                        best_brightness = b
                        CAPTURE_STATUS["last_max_brightness"] = b
                time.sleep(0.05) # Sample at ~20fps if camera/Pi allows
            
            CAPTURE_STATUS["stage"] = "ANALYSIS"
            CAPTURE_STATUS["progress"] = 95

            if burst_frames:
                # Pick the brightest frame from the entire window
                burst_frames.sort(key=lambda x: x[0], reverse=True)
                best_brightness, best_frame = burst_frames[0]
                print(f"[UV] Burst complete. Max brightness found: {best_brightness:.1f} ({len(burst_frames)} frames sampled)")
            else:
                print("[UV] ERROR: No frames captured during burst.")
                best_frame = grab_frame()

        else:
            # Standard Timed Logic
            warmup = request.json.get("warmup", DETECTION_CONFIG["uv_warmup"]) if request.json else DETECTION_CONFIG["uv_warmup"]
            warmup = min(max(warmup, 1.0), 30.0)
            time.sleep(warmup)

            with camera_lock:
                if camera and camera.isOpened():
                    interval = window / max(samples, 1)
                    for i in range(samples):
                        frame = grab_frame()
                        if frame is not None:
                            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                            brightness = float(gray.mean())
                            if brightness > best_brightness:
                                best_brightness = brightness
                                best_frame = frame
                        time.sleep(interval)

        # 4. Turn UV OFF
        send_mega_command("UV:OFF")

        if best_frame is None:
            return jsonify({"status": "error", "message": "Camera frame capture failed"}), 503

        print(f"[UV] Final best frame brightness: {best_brightness:.1f}")

        # Rotate
        best_frame = cv2.rotate(best_frame, cv2.ROTATE_90_CLOCKWISE)

        # 5. Oil fluorescence analysis
        analysis = analyze_fluorescence(best_frame)

        # Encode
        ret, buffer = cv2.imencode('.jpg', best_frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not ret:
            return jsonify({"status": "error", "message": "JPEG encoding failed"}), 500

        frame_bytes = buffer.tobytes()
        frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
        now = time.time()

        # Push alert to OpsCenter
        try:
            r = requests.post(config["api_endpoint"], json={
                "score": analysis["score"],
                "regions": analysis["regions"],
                "coverage_pct": analysis["coverage_pct"],
                "fluor_pixels": analysis["fluor_pixels"],
                "timestamp": now,
                "thumbnail_b64": frame_b64
            }, timeout=3)
            print(f"[UV] Capture pushed to Obs Center: {r.status_code}")
        except Exception as e:
            print(f"[UV] Obs Center push failed: {e}")

        # Push snapshot to OpsCenter
        try:
            ops_url = config.get("api_endpoint", "").replace("/alert", "/snapshot")
            r = requests.post(ops_url, json={
                "snapshot_b64": frame_b64,
                "timestamp": now
            }, timeout=3)
        except:
            pass

        # Upload to FTP
        ftp_upload_snapshot(frame_bytes, now)

        CAPTURE_STATUS["active"] = False
        CAPTURE_STATUS["stage"] = "IDLE"
        CAPTURE_STATUS["progress"] = 100

        return jsonify({
            "status": "success",
            "frame_b64": frame_b64,
            "timestamp": now,
            "warmup": warmup,
            "analysis": analysis
        })

    finally:
        CAPTURE_STATUS["active"] = False
        uv_lock.release()


@app.route('/api/safety/snapshot', methods=['GET'])
def safety_snapshot():
    """Grab a normal-light camera frame + sensor readings for safety panel.
    Called every 2s by the dashboard."""
    frame = grab_frame(retries=1)
    if frame is None:
        return jsonify({"status": "error", "message": "Camera unavailable"}), 503

    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    if not ret:
        return jsonify({"status": "error", "message": "JPEG encode failed"}), 500

    frame_b64 = base64.b64encode(buffer.tobytes()).decode('utf-8')

    # Read safety sensors from Mega
    safety_resp = send_mega_command("SAFETY")
    dist = None
    pir = None

    if safety_resp and safety_resp.startswith("SAFETY:OK:"):
        parts = safety_resp[len("SAFETY:OK:"):].split(",")
        for p in parts:
            if p.startswith("DIST="):
                val = p[5:]
                if val != "NO_ECHO":
                    try: dist = float(val)
                    except: pass
            elif p.startswith("PIR="):
                pir = p[4:]  # "MOTION" or "CLEAR"

    return jsonify({
        "status": "success",
        "frame_b64": frame_b64,
        "timestamp": time.time(),
        "distance_cm": dist,
        "pir": pir
    })


@app.route('/api/detection/config', methods=['GET', 'POST'])
def detection_config():
    """Get or update detection tuning parameters."""
    if request.method == 'GET':
        return jsonify({"status": "success", "config": DETECTION_CONFIG})

    data = request.json
    if not data:
        return jsonify({"status": "error", "message": "No JSON body"}), 400

    updated = []
    for key in data:
        if key in DETECTION_CONFIG:
            old_val = DETECTION_CONFIG[key]
            DETECTION_CONFIG[key] = type(old_val)(data[key])
            updated.append(f"{key}: {old_val} -> {DETECTION_CONFIG[key]}")
            print(f"[DETECTION] Config updated: {key} = {DETECTION_CONFIG[key]}")

    if not updated:
        return jsonify({"status": "error", "message": "No valid config keys provided"}), 400

    return jsonify({"status": "success", "updated": updated, "config": DETECTION_CONFIG})


@app.route('/status')
def status():
    safe_config = {k: v for k, v in config.items() if 'pass' not in k}
    return jsonify({
        "online": True,
        "config": safe_config
    })


def sampler_loop():
    """Background thread for the 'Night Hunter' automatic sampler."""
    print("[SAMPLER] Night Hunter thread started")
    while True:
        try:
            if DETECTION_CONFIG.get("sampler_enabled"):
                now = datetime.now()
                hour = now.hour
                start = DETECTION_CONFIG["sampler_start_hour"]
                end = DETECTION_CONFIG["sampler_end_hour"]
                
                # Check if we are within the sampling window (handles overnight crossing)
                is_active = False
                if start < end:
                    is_active = start <= hour < end
                else: # Overnight window (e.g. 22 to 06)
                    is_active = hour >= start or hour < end
                
                if is_active:
                    print(f"[SAMPLER] Window active ({hour}h). Triggering automated UV capture...")
                    # Proxy internal call to the capture logic
                    # We do this via a local HTTP call to ensure locks and logic stay consistent
                    try:
                        requests.post("http://127.0.0.1:5050/api/uv/capture", json={"reason": "sampler"}, timeout=45)
                    except Exception as e:
                        print(f"[SAMPLER] Trigger failed: {e}")
                    
                    # Sleep for the interval
                    interval_s = DETECTION_CONFIG["sampler_interval_min"] * 60
                    print(f"[SAMPLER] Capture complete. Sleeping for {DETECTION_CONFIG['sampler_interval_min']}m")
                    time.sleep(interval_s)
                else:
                    # Outside window, check again in 5 minutes
                    time.sleep(300)
            else:
                # Disabled, check again in 30 seconds
                time.sleep(30)
        except Exception as e:
            print(f"[SAMPLER] Loop error: {e}")
            time.sleep(60)


if __name__ == "__main__":
    from datetime import datetime
    # Initialize camera once at startup (kept open for on-demand capture)
    camera = init_camera()
    
    # Start Night Hunter thread
    sampler_thread = threading.Thread(target=sampler_loop, daemon=True)
    sampler_thread.start()
    
    print("[VISION] Service ready — camera idle, waiting for UV capture commands")
    app.run(host='0.0.0.0', port=5050, threaded=True)
