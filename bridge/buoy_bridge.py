#!/usr/bin/env python3
import time
import json
import sys
import argparse
import os
import subprocess

# Local imports
try:
    import lora_handler
    from main_bridge import MainBridge
    from health_bridge import HealthBridge
    from lora_handler import LoraHandler
except ImportError:
    # Fallback for parent directory execution
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    import lora_handler
    from main_bridge import MainBridge
    from health_bridge import HealthBridge
    from lora_handler import LoraHandler

# Buoy Bridge: Unified listener for downstream LoRa commands
# Runs on BOTH Main Pi and Health Pi

def main():
    parser = argparse.ArgumentParser(description="OceanPulse Buoy LoRa Bridge")
    parser.add_argument("--circuit", required=True, choices=['M', 'H'], help="Circuit ID (M=Main, H=Health)")
    parser.add_argument("--lora-port", default='/dev/ttyUSB0', help="LoRa Serial Port")
    parser.add_argument("--mega-port", default='/dev/ttyACM0', help="Arduino Mega Serial Port")
    args = parser.parse_args()

    circuit_id = args.circuit
    print(f"Starting Buoy LoRa Bridge for Circuit {circuit_id}")

    # Initialize local hardware bridge
    if circuit_id == 'M':
        mega_bridge = MainBridge(port=args.mega_port)
    else:
        mega_bridge = HealthBridge(port=args.mega_port)

    lora = LoraHandler(port=args.lora_port, mode='AT')
    
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
            # System A resets B, System B resets A
            if mega_bridge.connect():
                res = mega_bridge.reboot()
                print(f"Reset Result: {res}")
                mega_bridge.disconnect()
        
        elif cmd == "RELAY":
            # Direct relay control via LoRa
            if parts[3] in ["ON", "OFF"]:
                state = parts[3] == "ON"
                if mega_bridge.connect():
                    res = mega_bridge.set_relay(state)
                    print(f"Relay Result: {res}")
                    mega_bridge.disconnect()
        
        elif cmd == "PING":
            # Upstream ACK
            lora.send_text(f"{circuit_id}:PONG")

    if lora.connect():
        print("LoRa Connected. Listening for commands and reporting telemetry...")
        
        # We use a thread for listening so the main loop can handle periodic telemetry
        import threading
        listen_thread = threading.Thread(target=lora.listen, kwargs={'callback': on_lora_message}, daemon=True)
        listen_thread.start()

        try:
            while True:
                # 1. Collect Full Status Telemetry
                if mega_bridge.connect():
                    res = mega_bridge.get_status()
                    if res.get("status") == "success":
                        # Raw value: RELAY=OFF,TDS=450.0ppm,TEMP=25.0C,WD=OFF
                        # We strip the "ppm" and "C" for cleaner parsing on gateway
                        status_val = res.get("value")
                        clean_status = status_val.replace("ppm", "").replace("C", "").replace("%", "")
                        lora.send_text(f"{circuit_id}:STATUS={clean_status}")
                    mega_bridge.disconnect()
                
                # 2. Wait for next cycle
                time.sleep(30) # Report every 30 seconds
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            lora.close()

if __name__ == "__main__":
    main()
