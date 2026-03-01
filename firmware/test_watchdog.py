#!/usr/bin/env python3
import serial
import time
import sys

def test_watchdog(port='/dev/ttyACM0', baud=115200):
    print(f"Connecting to {port} at {baud}...")
    try:
        ser = serial.Serial(port, baud, timeout=2)
        # Prevent auto-reset if possible or wait for it
        ser.dtr = False 
        ser.rts = False
        time.sleep(3) # Wait for Arduino reset to complete
        ser.reset_input_buffer()
        
        # Flush initial boot messages
        print(f"Boot msg: {ser.read_all()}")
        
    except serial.SerialException as e:
        print(f"Error opening port: {e}")
        return

    commands = [
        ("PING", "PING:OK:ALIVE"),
        ("WATCHDOG:ENABLE", "WATCHDOG:OK:ENABLED"),
        ("STATUS", "WD=ON"),
        ("WATCHDOG:KICK", "WATCHDOG:OK:KICKED"),
        ("WATCHDOG:DISABLE", "WATCHDOG:OK:DISABLED"),
        ("STATUS", "WD=OFF")
    ]

    passed = 0
    total = len(commands)

    for cmd, expected in commands:
        print(f"TX: {cmd}")
        ser.write(f"{cmd}\n".encode('utf-8'))
        
        # Read response
        try:
            line = ser.readline().decode('utf-8').strip()
            print(f"RX: {line}")
            
            if expected in line:
                print(f"PASS: Found '{expected}'")
                passed += 1
            else:
                print(f"FAIL: Expected '{expected}'")
        except Exception as e:
            print(f"Error reading: {e}")

        time.sleep(0.5)

    print(f"\nTest Summary: {passed}/{total} Passed")
    ser.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        test_watchdog(sys.argv[1])
    else:
        test_watchdog()
