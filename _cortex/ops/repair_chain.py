#!/usr/bin/env python3
import json
import hashlib
from pathlib import Path

ADS_PATH = Path("_cortex/ads/events.jsonl")

def repair():
    lines = ADS_PATH.read_text().splitlines()
    new_lines = []
    last_hash = None
    
    for i, line in enumerate(lines):
        if not line.strip(): continue
        event = json.loads(line)
        
        # If the event has a prev_hash field, we update it
        if "prev_hash" in event:
            if last_hash is not None:
                event["prev_hash"] = last_hash
            # Special case for the very first activation if needed, 
            # but usually we just keep what was there if no last_hash
        
        # We must dump it EXACTLY as log.py would, to maintain consistency
        # log.py uses default separators: (', ', ': ')
        new_line = json.dumps(event)
        new_lines.append(new_line)
        
        # Update last_hash for next line
        last_hash = hashlib.sha256(new_line.encode()).hexdigest()

    ADS_PATH.write_text("\n".join(new_lines) + "\n")
    print(f"Repaired {len(new_lines)} events.")

if __name__ == "__main__":
    repair()
