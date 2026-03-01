import serial
import time
import sys

def kick_and_scan(port='/dev/ttyACM0'):
    print(f"Kicking {port}...")
    try:
        s = serial.Serial(port, 115200)
        # Aggressive Reset Pulse
        s.dtr = False
        s.rts = False
        time.sleep(0.5)
        s.dtr = True
        s.rts = True
        time.sleep(0.5)
        s.dtr = False
        time.sleep(0.5)
        s.close()
        print("Reset pulse sent.")
    except Exception as e:
        print(f"Failed to kick: {e}")

    # Now Scan
    rates = [115200, 9600]
    for baud in rates:
        print(f"Scanning {baud}...")
        try:
            s = serial.Serial(port, baud, timeout=2)
            time.sleep(2) # Wait for bootloader
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
    print("No response.")

if __name__ == "__main__":
    kick_and_scan()
