#!/usr/bin/env python3
import serial
import sys
import time

def read_vedirect(port='/dev/ttyUSB1'):
    """
    Reads the VE.Direct text protocol from a Victron MPPT.
    Default port is /dev/ttyUSB1 as per FIRMWARE_SPEC.md.
    """
    try:
        # VE.Direct uses 19200 baud, 8N1
        ser = serial.Serial(port, 19200, timeout=2)
        print(f"--- Listening for VE.Direct data on {port} (19200 baud) ---")
        print("Press Ctrl+C to stop.\n")
        
        while True:
            line = ser.readline().decode('ascii', errors='ignore').strip()
            if line:
                # Basic parsing for better readability
                if '\t' in line:
                    key, val = line.split('\t', 1)
                    # Convert common values to human-readable
                    if key == 'V':
                        print(f"Battery Voltage: {float(val)/1000:.2f} V")
                    elif key == 'I':
                        print(f"Charge Current: {float(val)/1000:.2f} A")
                    elif key == 'VPV':
                        print(f"Panel Voltage:  {float(val)/1000:.2f} V")
                    elif key == 'PPV':
                        print(f"Panel Power:    {val} W")
                    elif key == 'CS':
                        states = {'0':'Off', '2':'Fault', '3':'Bulk', '4':'Absorption', '5':'Float'}
                        print(f"Charge State:   {states.get(val, val)}")
                    else:
                        print(f"{key}: {val}")
                else:
                    # Checksum or other non-tabbed line
                    pass
            
    except serial.SerialException as e:
        print(f"Serial Error: {e}")
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()

if __name__ == "__main__":
    port = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyUSB1'
    read_vedirect(port)
