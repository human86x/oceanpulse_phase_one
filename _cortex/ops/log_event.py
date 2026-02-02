import sys
import os
import json
import time
import fcntl
import datetime
import argparse

ADS_PATH = "_cortex/ads/events.jsonl"
SCHEMA_PATH = "_cortex/ads/schema.json"

def generate_id():
    now = datetime.datetime.now()
    # Format: evt_YYYYMMDD_HHMMSS_XXX
    ms = int(now.microsecond / 1000)
    return f"evt_{now.strftime('%Y%m%d_%H%M%S')}_{ms:03d}"

def get_iso_timestamp():
    return datetime.datetime.now().isoformat()

def validate_event(event, schema):
    # Basic manual validation
    required = schema.get("required", [])
    for field in required:
        if field not in event:
            raise ValueError(f"Missing required field: {field}")
            
    props = schema.get("properties", {})
    
    # Agent Validation
    if event["agent"] not in props["agent"]["enum"]:
        raise ValueError(f"Invalid agent: {event['agent']}")
    
    # Action Type Validation
    if event["action_type"] not in props["action_type"]["enum"]:
        # Allow 'file_check' or other minor variations if needed, but strictly follow schema for now
        raise ValueError(f"Invalid action_type: {event['action_type']}")

    return True

def log_event(args):
    # Construct Event
    event = {
        "id": generate_id(),
        "ts": get_iso_timestamp(),
        "session_id": args.session_id,
        "agent": args.agent,
        "role": args.role,
        "action_type": args.action_type,
        "spec_ref": args.spec_ref if args.spec_ref != "null" else None,
        "authority": args.authority,
        "authorized": args.authorized,
        "rationale": args.rationale,
        "action_data": json.loads(args.action_data) if args.action_data else {},
        "outcome": args.outcome,
        "escalation": args.escalation
    }

    # Load Schema for validation
    try:
        with open(SCHEMA_PATH, 'r') as f:
            schema = json.load(f)
        validate_event(event, schema)
    except Exception as e:
        raise ValueError(f"Validation failed: {str(e)}")

    # Append to ADS with File Locking
    try:
        with open(ADS_PATH, 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                f.write(json.dumps(event) + "\n")
                f.flush()
                os.fsync(f.fileno()) # Ensure write to disk
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
    except Exception as e:
        raise IOError(f"Failed to write to ADS: {str(e)}")
    
    print(json.dumps({"status": "success", "event_id": event["id"]}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_id", required=True)
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
    try:
        log_event(args)
    except Exception as e:
        # Output JSON error so calling agent can parse it
        print(json.dumps({"status": "error", "message": str(e)}))
        sys.exit(1)
