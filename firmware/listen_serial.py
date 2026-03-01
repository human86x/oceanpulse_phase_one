import serial
import time
import sys

def listen(port='/dev/ttyACM0', baud=115200):
    print(f"Listening on {port} at {baud}...")
    s = serial.Serial(port, baud, timeout=0.1)
    s.dtr = False
    time.sleep(1)
    s.dtr = True
    try:
        while True:
            data = s.read_all()
            if data:
                print(f"Got: {data}")
            time.sleep(0.1)
    except KeyboardInterrupt:
        s.close()

if __name__ == "__main__":
    p = sys.argv[1] if len(sys.argv) > 1 else '/dev/ttyACM0'
    listen(p)
