#!/usr/bin/env python3
"""
ADT Seed Generator
Creates a portable 'adt_bootstrap.py' script that can reinstall the current
ADT Framework (Governance, Panel, Logging, Ops) into any new project.
"""

import os
import base64

# Files to include in the seed
FILES = [
    "_cortex/ADT_CONSTITUTION.md",
    "_cortex/AI_PROTOCOL.md",
    "_cortex/AGENTS.md",
    "_cortex/ops/log.py",
    "_cortex/roles/Overseer/compile_ads.py",
    "ops/backup_ads.sh",
    "adt_panel/index.html",
    "adt_panel/style.css",
    "adt_panel/panel.js",
    "adt_panel/about.html",
    "adt_panel/deploy.sh"
]

OUTPUT_FILE = "adt_bootstrap.py"

BOOTSTRAP_HEADER = """#!/usr/bin/env python3
# ADT Framework Bootstrap
# Generated from OceanPulse Phase One
#
# Usage: python3 adt_bootstrap.py
# This will hydrate the _cortex/, ops/, and adt_panel/ structures.

import os
import sys
import base64
from pathlib import Path

def write_file(path, content_b64):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "wb") as f:
        f.write(base64.b64decode(content_b64))
    print(f"✅ Created: {path}")
    
    # Make scripts executable
    if path.endswith(".sh") or path.endswith(".py"):
        os.chmod(path, 0o755)

def main():
    print("=== Hydrating ADT Framework ===")
    
    # Creates empty critical dirs
    dirs = [
        "_cortex/ads",
        "_cortex/specs", 
        "_cortex/work_logs",
        "_cortex/active_tasks"
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
        print(f"✅ Directory: {d}")

"""

def sanitize_content(filename, content):
    """Remove project-specific secrets"""
    text = content.decode('utf-8')
    
    if filename == "adt_panel/deploy.sh":
        text = text.replace('HOST="ftp.oceanpulse.pt"', 'HOST="your-ftp-host.com"')
        text = text.replace('USER="oceanpul"', 'USER="your-user"')
        text = text.replace('PASS="sagres_2025Xx"', 'PASS="your-password"')
        text = text.replace('REMOTE_PATH="public_html/adt_panel"', 'REMOTE_PATH="public_html/panel"')
        text = text.replace('URL: https://oceanpulse.pt/adt_panel/', 'URL: http://your-site.com/panel/')
        
    return text.encode('utf-8')

def generate_seed():
    with open(OUTPUT_FILE, "w") as f:
        f.write(BOOTSTRAP_HEADER)
        f.write("\n    # File Definitions\n")
        
        for filepath in FILES:
            if not os.path.exists(filepath):
                print(f"⚠️ Warning: Skipping missing file {filepath}")
                continue
                
            with open(filepath, "rb") as source:
                content = source.read()
                
            # Sanitize
            content = sanitize_content(filepath, content)
            
            # Encode
            b64 = base64.b64encode(content).decode('utf-8')
            
            f.write(f'    write_file("{filepath}", "{b64}")\n')
            
        # Initialize Schema (Encoded safely as b64 to avoid string escape issues)
        schema_json = b"""{ 
  "type": "object",
  "required": ["id", "ts", "agent", "action_type", "spec_ref", "authority"],
  "properties": {
    "agent": {"type": "string", "enum": ["CLAUDE", "GEMINI"]},
    "action_type": {"type": "string"}
  }
}"""
        schema_b64 = base64.b64encode(schema_json).decode('utf-8')
        f.write(f'    write_file("_cortex/ads/schema.json", "{schema_b64}")\n')

        # Robust print statements
        f.write('\n    print("\\n🎉 ADT Framework Installed Successfully.")\n')
        f.write('    print("Next Steps:")\n')
        f.write('    print("1. Review _cortex/ADT_CONSTITUTION.md")\n')
        f.write('    print("2. Configure adt_panel/deploy.sh with your hosting credentials")\n')
        f.write('    print("3. Start working! (Logs will go to _cortex/ads/events.jsonl)")\n')
        f.write('\nif __name__ == "__main__":\n    main()\n')
    
    os.chmod(OUTPUT_FILE, 0o755)
    print(f"🌱 Seed generated: {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_seed()