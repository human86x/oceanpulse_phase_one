#!/usr/bin/env python3
try:
    import meshtastic
    import meshtastic.serial_interface
    HAS_MESHTASTIC = True
except ImportError:
    HAS_MESHTASTIC = False

import sys
import time
import argparse

def main():
    parser = argparse.ArgumentParser(description="OceanPulse LoRa-E5 Tester")
    parser.add_argument("--port", help="Serial port for LoRa-E5 (e.g. /dev/ttyUSB0)", default=None)
    parser.add_argument("--info", action="store_true", help="Display module info")
    parser.add_argument("--raw", action="store_true", help="Attempt raw serial communication")
    parser.add_argument("--baud", type=int, default=115200, help="Baud rate for raw communication")
    parser.add_argument("--at", action="store_true", help="Use LoRa-E5 AT Command mode")
    args = parser.parse_args()

    if args.at:
        if not args.port:
            print("Error: --port required for AT mode.")
            sys.exit(1)
        try:
            import serial
            ser = serial.Serial(args.port, 9600, timeout=2)
            print(f"LoRa-E5 AT Command Mode on {args.port} (9600 baud)")
            
            def send_at(cmd):
                print(f"TX: {cmd}")
                ser.write(f"{cmd}\r\n".encode())
                time.sleep(0.5)
                res = ser.read(1024).decode(errors='ignore')
                print(f"RX: {res.strip()}")
                return res

            send_at("AT")
            send_at("AT+VER")
            send_at("AT+ID")
            send_at("AT+MODE=TEST")
            send_at("AT+TEST=TX,\"PING\"")
            
            ser.close()
            return
        except Exception as e:
            print(f"AT mode error: {e}")
            sys.exit(1)

    if args.raw:
        if not args.port:
            print("Error: --port required for raw mode.")
            sys.exit(1)
        try:
            import serial
            print(f"Opening raw serial connection on {args.port} at {args.baud} baud...")
            ser = serial.Serial(args.port, args.baud, timeout=2)
            
            # Try some common triggers
            print("Sending test sequences...")
            ser.write(b"\r\n") # Enter
            time.sleep(0.5)
            ser.write(b"AT\r\n") # AT command
            time.sleep(0.5)
            ser.write(b"help\r\n") # Help
            time.sleep(0.5)
            
            response = ser.read(1024)
            if response:
                print(f"Received response: {response}")
                print(f"Decoded: {response.decode(errors='ignore')}")
            else:
                print("No response received.")
            ser.close()
            return
        except Exception as e:
            print(f"Raw serial error: {e}")
            sys.exit(1)

    if not HAS_MESHTASTIC:
        print("Error: Meshtastic library not found. Use --at or --raw mode.")
        sys.exit(1)

    try:
        print("Searching for LoRa-E5 module...")
        interface = meshtastic.serial_interface.SerialInterface(devPath=args.port)
        
        if args.info:
            print("\n--- Module Info ---")
            if hasattr(interface, 'nodes'):
                 print(f"Nodes in Mesh: {len(interface.nodes)}")
            if hasattr(interface, 'myInfo'):
                 print(f"My Node ID: {interface.myInfo.my_node_num}")
            if hasattr(interface, 'metadata'):
                 print(f"Model: {interface.metadata.hw_model}")
            print("-------------------\n")
        
        interface.close()
        print("Check completed successfully.")

    except Exception as e:
        print(f"Error connecting to LoRa module: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()