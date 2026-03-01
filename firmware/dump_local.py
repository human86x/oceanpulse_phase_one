import serial
import time

ser = serial.Serial('/dev/ttyACM0', 115200, timeout=0.1)
print("Opened port. Reset the Arduino now.")
try:
    while True:
        if ser.in_waiting > 0:
            print(ser.read(ser.in_waiting))
        time.sleep(0.01)
except KeyboardInterrupt:
    ser.close()
