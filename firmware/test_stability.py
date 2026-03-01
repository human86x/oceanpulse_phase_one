#!/usr/bin/env python3
import serial
import time
import sys

PORT = '/dev/ttyACM0'
BAUD = 115200

def send_cmd(ser, cmd):
    ser.write((cmd + "\n").encode())
    res = ser.readline().decode().strip()
    return res

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        time.sleep(2)
        ser.reset_input_buffer()

        print("Testing stability (5 reads)...")
        for i in range(5):
            res = send_cmd(ser, "TDS:READ")
            print(f"Read {i+1}: {res}")
            time.sleep(1)
        
        print("\nFinal Status:")
        print(send_cmd(ser, "STATUS"))

        ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()