#!/usr/bin/env python3
import serial
import time
import json
import sys

class HealthBridge:
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
            self.ser.reset_input_buffer()
            full_cmd = f"{cmd}\n".encode('utf-8')
            self.ser.write(full_cmd)
            response = self.ser.readline().decode().strip()
            
            if not response:
                return {"status": "error", "message": "No response"}
            
            parts = response.split(':')
            if len(parts) >= 2 and parts[1] == "OK":
                return {
                    "status": "success", 
                    "command": parts[0], 
                    "value": parts[2] if len(parts) > 2 else None
                }
            
            return {"status": "unknown", "raw": response}
            
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def ping(self):
        return self._send_command("PING")

def monitor_loop(interval=10):
    bridge = HealthBridge()
    if not bridge.connect():
        sys.exit(1)
        
    print(f"Starting Health Monitor on {bridge.port}...")
    try:
        while True:
            result = bridge.ping()
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {json.dumps(result)}")
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    finally:
        bridge.disconnect()

if __name__ == "__main__":
    monitor_loop()
