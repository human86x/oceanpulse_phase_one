#!/usr/bin/env python3
import serial
import time
import json
import sys
import argparse
import os

# Ensure we can import from local directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from lora_handler import LoraHandler
except ImportError:
    LoraHandler = None
    print("Warning: lora_handler module not found. LoRa features disabled.", file=sys.stderr)

class HealthBridge:
    def __init__(self, port='/dev/op-mega', baud=115200):
        self.port = port
        self.baud = baud
        self.ser = None

    def connect(self):
        # IDEMPOTENT — keeping the port open across polls is the only way to
        # avoid the Mega auto-reset on every cdc_acm open() (DTR pulse always
        # fires at open time on Linux cdc_acm, regardless of dtr=False). When
        # the port is opened repeatedly the Mega reboots → pin 38 floats during
        # bootloader → cross-circuit reboot relay clicks every poll. This kept
        # state means open() runs once per process lifetime; recovery (USB
        # rebind) closes via release() and the next call reopens cleanly.
        if self.ser is not None and self.ser.is_open:
            return True
        try:
            import subprocess
            subprocess.run(["stty", "-F", self.port, "-hupcl"],
                          capture_output=True, timeout=2)
            self.ser = serial.Serial()
            self.ser.port = self.port
            self.ser.baudrate = self.baud
            self.ser.timeout = 2
            self.ser.dtr = False
            self.ser.rts = False
            self.ser.open()
            time.sleep(2)  # one-time wait for Mega boot after first open
            self.ser.reset_input_buffer()
            return True
        except serial.SerialException as e:
            print(f"Error connecting to {self.port}: {e}", file=sys.stderr)
            self.ser = None
            return False

    def disconnect(self):
        # NO-OP by design. See connect() docstring. Use release() to actually
        # close the port (only the auto-recovery path needs that).
        pass

    def release(self):
        if self.ser and self.ser.is_open:
            try: self.ser.close()
            except Exception: pass
        self.ser = None

    def _send_command(self, cmd):
        if not self.ser or not self.ser.is_open:
            return {"status": "error", "message": "Not connected"}

        try:
            self.ser.reset_input_buffer()
            full_cmd = f"{cmd}\n".encode('utf-8')
            self.ser.write(full_cmd)
            response = self.ser.readline().decode().strip()
        except (OSError, serial.SerialException) as e:
            print(f"Serial I/O error on {self.port}: {e} — releasing handle", file=sys.stderr)
            self.release()
            return {"status": "error", "message": f"serial error: {e}"}

        try:
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

    def reboot(self):
        """Triggers hardware reset of the OTHER circuit (SPEC-002)."""
        return self._send_command("REBOOT:SYS")

    def get_status(self):
        """Gets full status string from Arduino."""
        return self._send_command("STATUS")

def monitor_loop(bridge, lora=None, interval=10):
    if not bridge.connect():
        sys.exit(1)
        
    print(f"Starting Health Monitor on {bridge.port}...")
    if lora:
        print("LoRa reporting ENABLED.")

    try:
        while True:
            # 1. Local Heartbeat
            result = bridge.ping()
            status_json = json.dumps(result)
            print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {status_json}")
            
            # 2. LoRa Reporting (if enabled and successful local ping)
            if lora and result.get("status") == "success":
                # H:STATUS=OK;UPTIME=... (Future expansion)
                # For now just simple alive signal
                msg = "H:ALIVE"
                lora.broadcast(msg)
            elif lora and result.get("status") != "success":
                # Critical: Arduino lost?
                lora.broadcast("H:ERROR:ARDUINO_LOST")

            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
    finally:
        bridge.disconnect()
        if lora:
            lora.close()

def main():
    parser = argparse.ArgumentParser(description="OceanPulse Health Bridge")
    parser.add_argument("--port", default='/dev/ttyACM0', help="Arduino Serial Port")
    parser.add_argument("--lora-port", default='/dev/ttyUSB0', help="LoRa Serial Port")
    parser.add_argument("--lora-mode", default='AT', choices=['AT', 'MESHTASTIC'], help="LoRa mode")
    parser.add_argument("--lora-baud", type=int, default=9600, help="LoRa baud rate")
    parser.add_argument("--lora", action="store_true", help="Enable LoRa transmission")
    parser.add_argument("--interval", type=int, default=10, help="Monitor interval in seconds")
    parser.add_argument("--command", help="One-off command (PING)")
    
    args = parser.parse_args()

    bridge = HealthBridge(port=args.port)
    lora = None
    
    if args.lora and LoraHandler:
        lora = LoraHandler(port=args.lora_port, baud=args.lora_baud, mode=args.lora_mode)
        lora.connect()

    if args.command:
        # One-off mode
        if not bridge.connect():
            sys.exit(1)
        cmd = args.command.upper()
        if cmd == "PING":
            print(json.dumps(bridge.ping()))
        elif cmd == "REBOOT":
            print(json.dumps(bridge.reboot()))
        elif cmd == "STATUS":
            print(json.dumps(bridge.get_status()))
        bridge.disconnect()
        if lora:
            lora.close()
    else:
        # Monitor mode
        monitor_loop(bridge, lora, args.interval)

if __name__ == "__main__":
    main()