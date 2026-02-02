#!/usr/bin/env python3
"""Quick serial test for Arduino firmware"""

import serial
import sys
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
BAUD = 115200

def test():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
    except serial.SerialException as e:
        print(f"Error opening port {PORT}: {e}")
        sys.exit(1)

    time.sleep(2)  # Wait for Arduino reset

    # Clear buffer
    ser.reset_input_buffer()

    # Test PING
    print(f"Sending PING to {PORT}...")
    ser.write(b'PING\n')
    response = ser.readline().decode().strip()
    print(f"PING -> {response}")
    
    if response == "PING:OK:ALIVE":
        print("SUCCESS: Arduino is responsive.")
    else:
        print(f"FAILURE: Expected 'PING:OK:ALIVE', got '{response}'")
        sys.exit(1)

    print("All tests passed!")
    ser.close()

if __name__ == "__main__":
    test()