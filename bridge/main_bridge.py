#!/usr/bin/env python3
import serial
import time
import json
import sys

class MainBridge:
    def __init__(self, port='/dev/ttyACM0', baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None

    def connect(self):
        try:
            self.ser = serial.Serial(self.port, self.baud, timeout=2)
            time.sleep(2)  # Wait for Arduino reset
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}", file=sys.stderr)
            return False

    def disconnect(self):
        if self.ser and self.ser.is_open:
            self.ser.close()

    def _send_command(self, cmd):
        if not self.ser or not self.ser.is_open:
            return {"status": "error", "message": "Not connected"}
        
        try:
            # Clear buffer
            self.ser.reset_input_buffer()
            
            # Send command
            full_cmd = f"{cmd}\n".encode('utf-8')
            self.ser.write(full_cmd)
            
            # Read response
            response = self.ser.readline().decode().strip()
            
            if not response:
                return {"status": "error", "message": "No response"}
            
            # Parse <CMD>:<STATUS>:<VALUE>
            parts = response.split(':')
            if len(parts) >= 2:
                # Handle standard OK response
                if parts[1] == "OK":
                    return {
                        "status": "success", 
                        "command": parts[0], 
                        "value": parts[2] if len(parts) > 2 else None
                    }
                # Handle ERROR response
                elif parts[0] == "ERROR":
                    return {"status": "error", "message": parts[1] if len(parts) > 1 else "Unknown error"}
            
            return {"status": "unknown", "raw": response}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ping(self):
        return self._send_command("PING")

    def set_relay(self, state):
        cmd = "RELAY:ON" if state else "RELAY:OFF"
        return self._send_command(cmd)

    def read_tds(self):
        return self._send_command("TDS:READ")

def main():
    bridge = MainBridge()
    if not bridge.connect():
        sys.exit(1)

    print(json.dumps(bridge.ping()))
    
    # Test sequence if arguments provided
    if len(sys.argv) > 1:
        cmd = sys.argv[1].upper()
        if cmd == "ON":
            print(json.dumps(bridge.set_relay(True)))
        elif cmd == "OFF":
            print(json.dumps(bridge.set_relay(False)))
        elif cmd == "TDS":
            print(json.dumps(bridge.read_tds()))
    
    bridge.disconnect()

if __name__ == "__main__":
    main()
