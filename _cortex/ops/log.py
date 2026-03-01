#!/usr/bin/env python3
"""
ADT Safe Logger (v3.0 - The Integrity Chain)
Replaces manual 'echo >>' logging with a safe, validated, atomic, and CRYPTOGRAPHICALLY LINKED process.

Features:
1. Validates JSON structure against schema.
2. Uses file locking (flock) to prevent concurrent write corruption.
3. Enforces timestamps from system time.
4. HASH CHAIN: Every event contains a SHA-256 hash of the previous event.
5. TRIGGERS GIT BACKUP immediately after write.
"""

import sys
import os
import json
import time
import fcntl
import datetime
import argparse
import subprocess
import hashlib
from pathlib import Path

# Paths
PROJECT_ROOT = Path(__file__).parent.parent.parent
ADS_PATH = PROJECT_ROOT / "_cortex" / "ads" / "events.jsonl"
SCHEMA_PATH = PROJECT_ROOT / "_cortex" / "ads" / "schema.json"
BACKUP_SCRIPT = PROJECT_ROOT / "ops" / "backup_ads.sh"

def generate_id():
    now = datetime.datetime.now(datetime.timezone.utc)
    # Format: evt_YYYYMMDD_HHMMSS_XXX
    ms = int(now.microsecond / 1000)
    return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{ms:03d}"

def get_iso_timestamp():
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def get_prev_hash():
    """Reads the last line of the ADS and returns its SHA-256 hash"""
    if not ADS_PATH.exists() or ADS_PATH.stat().st_size == 0:
        return "0" * 64 # Genesis block hash
    
    try:
        with open(ADS_PATH, "rb") as f:
            # Efficiently find the last line
            f.seek(0, os.SEEK_END)
            size = f.tell()
            if size == 0: return "0" * 64
            
            # Read backwards to find the last newline
            pos = size - 2
            while pos > 0:
                f.seek(pos)
                if f.read(1) == b"\n":
                    break
                pos -= 1
            
            last_line = f.read().strip()
            if not last_line: return "0" * 64
            
            return hashlib.sha256(last_line).hexdigest()
    except Exception:
        return "error_calculating_hash"

def validate_event(event):
    if not SCHEMA_PATH.exists(): return True
    try:
        with open(SCHEMA_PATH, 'r') as f:
            schema = json.load(f)
        required = schema.get("required", [])
        for field in required:
            if field not in event:
                raise ValueError(f"Missing required field: {field}")
        return True
    except Exception as e:
        raise ValueError(f"Validation failed: {str(e)}")

def trigger_backup():
    if BACKUP_SCRIPT.exists():
        try:
            subprocess.run([str(BACKUP_SCRIPT)], check=True, capture_output=True, text=True)
            return True, "Committed"
        except Exception as e:
            return False, str(e)
    return False, "Backup script not found"

def log_event(args):
    # Construct Action Data
    action_data = {}
    if args.action_data:
        try:
            action_data = json.loads(args.action_data) if isinstance(args.action_data, str) else args.action_data
        except json.JSONDecodeError:
            action_data = {"raw": str(args.action_data)}

    # Open file once for both reading prev_hash and appending
    try:
        # We use 'a+' to read and append
        with open(ADS_PATH, 'a+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                # 1. Calculate Previous Hash
                f.seek(0)
                lines = f.readlines()
                prev_hash = "0" * 64
                if lines:
                    last_line = lines[-1].strip()
                    if last_line:
                        prev_hash = hashlib.sha256(last_line.encode('utf-8')).hexdigest()

                # 2. Construct Event
                event = {
                    "id": generate_id(),
                    "ref_id": args.ref_id if args.ref_id != "null" else None,
                    "ts": get_iso_timestamp(),
                    "session_id": args.session_id,
                    "agent": args.agent,
                    "role": args.role,
                    "action_type": args.action_type,
                    "spec_ref": args.spec_ref if args.spec_ref != "null" else None,
                    "authority": args.authority,
                    "authorized": args.authorized,
                    "rationale": args.rationale,
                    "action_data": action_data,
                    "outcome": args.outcome,
                    "escalation": args.escalation,
                    "prev_hash": prev_hash # The Integrity Link
                }

                # 3. Validate
                validate_event(event)

                # 4. Write
                f.seek(0, os.SEEK_END)
                f.write(json.dumps(event) + "\n")
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)
    
    # 5. Trigger Backup
    backup_status, backup_msg = trigger_backup()
    
    print(json.dumps({
        "status": "success", 
        "event_id": event["id"],
        "integrity_hash": hashlib.sha256(json.dumps(event).encode()).hexdigest()[:12],
        "backup": "ok" if backup_status else "failed"
    }))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_id", required=True)
    parser.add_argument("--ref_id", default="null")
    parser.add_argument("--agent", required=True, choices=["CLAUDE", "GEMINI"])
    parser.add_argument("--role", required=True)
    parser.add_argument("--action_type", required=True)
    parser.add_argument("--spec_ref", default="null")
    parser.add_argument("--authority", required=True)
    parser.add_argument("--authorized", type=lambda x: (str(x).lower() == 'true'), required=True)
    parser.add_argument("--rationale", default="")
    parser.add_argument("--action_data", default="{}")
    parser.add_argument("--outcome", default="pending")
    parser.add_argument("--escalation", type=lambda x: (str(x).lower() == 'true'), default=False)

    args = parser.parse_args()
    log_event(args)