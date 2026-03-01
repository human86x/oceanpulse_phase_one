#!/usr/bin/env python3
import serial
import time
import sys

def scan_baud(port='/dev/ttyACM0'):
    rates = [9600, 115200, 57600, 38400]
    for baud in rates:
        print(f"Testing {baud}...")
        try:
            s = serial.Serial(port, baud, timeout=2)
            time.sleep(2)
            s.write(b"PING\n")
            time.sleep(0.5)
            resp = s.read_all()
            if len(resp) > 0:
                print(f"SUCCESS at {baud}: {resp}")
                s.close()
                return
            s.close()
        except:
            pass
    print("No response on any baud rate.")

if __name__ == "__main__":
    scan_baud()
