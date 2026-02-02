#!/usr/bin/env python3
"""
ADT Overseer: ADS Compiler
Compiles events.jsonl to data.json for the oversight panel.

Per ADT Framework (Sheridan, 2026):
"A single Authoritative Data Source feeds all dashboards, controls and reports."
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

def compile_ads(ads_path: str, output_path: str):
    """Compile events.jsonl to structured data.json"""

    events = []
    by_agent = defaultdict(int)
    by_spec = defaultdict(int)
    by_type = defaultdict(int)
    authorized_count = 0
    unauthorized_count = 0
    escalations = []

    # Read events.jsonl
    ads_file = Path(ads_path)
    if not ads_file.exists():
        print(f"Error: ADS file not found: {ads_path}")
        sys.exit(1)

    with open(ads_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
                events.append(event)

                # Count by agent
                agent = event.get('agent', 'UNKNOWN')
                by_agent[agent] += 1

                # Count by spec
                spec = event.get('spec_ref')
                if spec:
                    by_spec[spec] += 1

                # Count by type
                action_type = event.get('action_type', 'unknown')
                by_type[action_type] += 1

                # Count compliance
                if event.get('authorized', False):
                    authorized_count += 1
                else:
                    unauthorized_count += 1

                # Collect escalations
                if event.get('escalation', False):
                    escalations.append(event)

            except json.JSONDecodeError as e:
                print(f"Warning: Invalid JSON line: {e}")
                continue

    # Build output
    output = {
        "last_sync": datetime.utcnow().isoformat() + "Z",
        "total_events": len(events),
        "by_agent": dict(by_agent),
        "by_spec": dict(by_spec),
        "by_type": dict(by_type),
        "compliance": {
            "authorized": authorized_count,
            "unauthorized": unauthorized_count
        },
        "escalations": escalations[-10:],  # Last 10 escalations
        "events": events[-200:],  # Last 200 events for timeline
        "tasks": []
    }

    # Read tasks.json if it exists
    tasks_path = project_root / "_cortex" / "tasks.json"
    if tasks_path.exists():
        try:
            with open(tasks_path, 'r') as f:
                tasks_data = json.load(f)
                output["tasks"] = tasks_data.get("tasks", [])
            print(f"Included {len(output['tasks'])} tasks from {tasks_path}")
        except json.JSONDecodeError as e:
            print(f"Warning: Invalid JSON in tasks.json: {e}")

    # Read requests.md if it exists
    requests_path = project_root / "_cortex" / "requests.md"
    parsed_requests = []
    if requests_path.exists():
        try:
            content = requests_path.read_text(encoding='utf-8')
            # Simple parsing of markdown requests
            current_req = {}
            for line in content.splitlines():
                line = line.strip()
                if line.startswith("## Request:"):
                    if current_req:
                        parsed_requests.append(current_req)
                    current_req = {"id": line.replace("## Request:", "").strip()}
                elif line.startswith("- **From:**"):
                    current_req["from"] = line.replace("- **From:**", "").strip()
                elif line.startswith("- **To:**"):
                    current_req["to"] = line.replace("- **To:**", "").strip()
                elif line.startswith("- **Subject:**"):
                    current_req["subject"] = line.replace("- **Subject:**", "").strip()
                elif line.startswith("- **Status:**"):
                    current_req["status"] = line.replace("- **Status:**", "").strip()
            if current_req:
                parsed_requests.append(current_req)
            
            output["requests"] = parsed_requests
            print(f"Included {len(parsed_requests)} requests from {requests_path}")
        except Exception as e:
            print(f"Warning: Could not read requests.md: {e}")

    # Collect Specs Content
    specs_content = {}
    specs_dir = project_root / "_cortex" / "specs"
    if specs_dir.exists():
        for spec_file in specs_dir.glob("**/*.md"):
            try:
                content = spec_file.read_text(encoding='utf-8')
                # Key by filename
                specs_content[spec_file.name] = content
                # Try to extract SPEC-XXX from filename
                if spec_file.name.startswith("SPEC-"):
                    spec_id = spec_file.name.split("_")[0].replace(".md", "")
                    specs_content[spec_id] = content
            except Exception as e:
                print(f"Warning: Could not read spec {spec_file}: {e}")
    
    output["specs_content"] = specs_content
    print(f"Included {len(specs_content)} spec documents")

    # Write output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Compiled {len(events)} events to {output_path}")
    print(f"  Authorized: {authorized_count}, Unauthorized: {unauthorized_count}")
    print(f"  Escalations: {len(escalations)}")

    return output

if __name__ == "__main__":
    # Default paths
    project_root = Path(__file__).parent.parent.parent.parent
    ads_path = project_root / "_cortex" / "ads" / "events.jsonl"
    output_path = project_root / "adt_panel" / "data.json"

    # Allow override via args
    if len(sys.argv) > 1:
        ads_path = Path(sys.argv[1])
    if len(sys.argv) > 2:
        output_path = Path(sys.argv[2])

    compile_ads(str(ads_path), str(output_path))
