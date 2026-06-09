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

class MainBridge:
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
            # Clear buffer
            self.ser.reset_input_buffer()

            # Send command
            full_cmd = f"{cmd}\n".encode('utf-8')
            self.ser.write(full_cmd)

            # Read response
            response = self.ser.readline().decode().strip()
        except (OSError, serial.SerialException) as e:
            # USB likely unbound (recovery, hotplug). Invalidate handle so the
            # next connect() reopens after udev re-creates the symlink.
            print(f"Serial I/O error on {self.port}: {e} — releasing handle", file=sys.stderr)
            self.release()
            return {"status": "error", "message": f"serial error: {e}"}

        try:
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

    def reboot(self):
        """Triggers hardware reset of the OTHER circuit (SPEC-002)."""
        return self._send_command("REBOOT:SYS")

    def get_status(self):
        """Gets full status string from Arduino and parses key-value pairs."""
        res = self._send_command("STATUS")
        if res.get("status") == "success" and res.get("value"):
            # Raw value: EC=OFFLINE,TDS=1392.7,WD=ON
            # Or: EC=12.34,TDS=450.0,WD=ON
            raw_val = res["value"]
            parsed = {}
            for pair in raw_val.split(','):
                if '=' in pair:
                    k, v = pair.split('=', 1)
                    # Convert to float if possible, else keep string
                    try:
                        parsed[k.lower()] = float(v)
                    except ValueError:
                        parsed[k.lower()] = v
            res["data"] = parsed
        return res

def main():
    parser = argparse.ArgumentParser(description="OceanPulse Main Bridge")
    parser.add_argument("--port", default='/dev/ttyACM0', help="Arduino Serial Port")
    parser.add_argument("--lora-port", default='/dev/ttyUSB0', help="LoRa Serial Port")
    parser.add_argument("--lora-mode", default='AT', choices=['AT', 'MESHTASTIC'], help="LoRa mode")
    parser.add_argument("--lora-baud", type=int, default=9600, help="LoRa baud rate")
    parser.add_argument("--lora", action="store_true", help="Enable LoRa transmission")
    parser.add_argument("--broadcast", help="Send specific message via LoRa (requires --lora)")
    parser.add_argument("command", nargs="?", help="Command: ON, OFF, TDS, PING, REBOOT, STATUS")
    
    args = parser.parse_args()

    bridge = MainBridge(port=args.port)
    lora = None
    
    if args.lora and LoraHandler:
        lora = LoraHandler(port=args.lora_port, baud=args.lora_baud, mode=args.lora_mode)
        lora.connect()
        
    if args.broadcast:
        if lora:
            lora.broadcast(args.broadcast)
            # If only broadcasting, we might not need to connect to Arduino
            if not args.command:
                print(json.dumps({"status": "success", "message": f"Broadcast: {args.broadcast}"}))
                lora.close()
                return
        else:
             print(json.dumps({"status": "error", "message": "LoRa not enabled or module missing"}), file=sys.stderr)
             if not args.command:
                 return

    if not bridge.connect():
        sys.exit(1)

    result = {}
    if args.command:
        cmd = args.command.upper()
        
        if cmd == "ON":
            result = bridge.set_relay(True)
        elif cmd == "OFF":
            result = bridge.set_relay(False)
        elif cmd == "TDS":
            result = bridge.read_tds()
            # If LoRa enabled and TDS read successful, send it
            if lora and result.get("status") == "success":
                val = result.get("value")
                # Format: M:TDS=123
                packet = f"M:TDS={val}"
                lora.send_text(packet)
        elif cmd == "PING":
            result = bridge.ping()
        elif cmd == "EC":
            result = bridge._send_command("EC:READ")
        elif cmd == "REBOOT":
            result = bridge.reboot()
        elif cmd == "STATUS":
            result = bridge.get_status()
        elif cmd in ("UV:ON", "UV:OFF"):
            result = bridge._send_command(cmd)
        else:
            result = {"status": "error", "message": f"Unknown command: {cmd}"}
    else:
        # Default behavior: PING
        result = bridge.ping()
    
    print(json.dumps(result))
    
    bridge.disconnect()
    if lora:
        lora.close()

if __name__ == "__main__":
    main()