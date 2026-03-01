#!/usr/bin/env python3
import serial
import time
import sys

PORT = '/dev/ttyACM0'
BAUD = 115200

def send_cmd(ser, cmd):
    print(f"TX: {cmd}")
    ser.write((cmd + "\n").encode())
    res = ser.readline().decode().strip()
    print(f"RX: {res}")
    return res

def main():
    try:
        ser = serial.Serial(PORT, BAUD, timeout=2)
        time.sleep(2)
        ser.reset_input_buffer()

        send_cmd(ser, "PING")
        send_cmd(ser, "UPTIME")
        send_cmd(ser, "TDS:READ")
        send_cmd(ser, "TDS:RAW")
        send_cmd(ser, "RELAY:ON")
        time.sleep(1)
        send_cmd(ser, "RELAY:STATUS")
        send_cmd(ser, "RELAY:OFF")
        send_cmd(ser, "STATUS")

        ser.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()