import cv2
import time
import serial
import os

class OilDetector:
    """
    OceanPulse System A: Mission Logic
    Handles safety-interlocked UV fluorescence capture and analysis.
    """
    def __init__(self, arduino_port='/dev/ttyACM0', baud_rate=9600):
        self.camera = cv2.VideoCapture(0)
        try:
            self.arduino = serial.Serial(arduino_port, baud_rate, timeout=1)
            time.sleep(2) # Wait for Arduino reboot
        except Exception as e:
            print(f"Warning: Could not connect to Arduino on {arduino_port}: {e}")
            self.arduino = None
        
    def check_hardware_safety(self):
        """Checks PIR and Ultrasonic sensors via Arduino"""
        if not self.arduino:
            return False
        
        self.arduino.write(b'GET_SAFETY\n')
        line = self.arduino.readline().decode('utf-8').strip()
        
        if line == "SAFE":
            return True
        else:
            print(f"Hardware Safety Veto: {line}")
            return False

    def detect_nav_lights(self, frame):
        """Passive scan for high-intensity lights (vessels)"""
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Check for pixels near saturation
        max_val = cv2.minMaxLoc(gray)[1]
        return max_val > 245

    def capture_sequence(self):
        """Executes the safety-interlocked strobe sequence"""
        
        # 1. Hardware Check (PIR/Sonic)
        if not self.check_hardware_safety():
            return None

        # 2. Visual Scan (Nav Lights)
        ret, pre_frame = self.camera.read()
        if not ret:
            print("Error: Camera failed")
            return None
            
        if self.detect_nav_lights(pre_frame):
            print("Safety Abort: Vessel or Navigation light detected.")
            return None

        # 3. Warning Phase (Amber Strobe)
        print("Safety Clear. Warning personnel...")
        if self.arduino:
            self.arduino.write(b'WARN_START\n')
            time.sleep(2.0)
            self.arduino.write(b'WARN_STOP\n')

        # 4. Trigger Pulse & Capture
        print("Firing UV Pulse...")
        if self.arduino:
            # Trigger 555 timer which limits pulse to 0.5s
            self.arduino.write(b'FIRE_UV\n')
            
        # Give inverter/light 100ms to ramp up
        time.sleep(0.1) 
        ret, frame = self.camera.read()
        
        return frame

    def analyze_fluorescence(self, frame):
        """Detects bright pixels caused by hydrocarbon fluorescence"""
        if frame is None: return 0
        
        # Focus on blue/white channel (typical diesel glow)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        # Threshold: keep only very bright pixels
        _, thresh = cv2.threshold(gray, 200, 255, cv2.THRESH_BINARY)
        
        # Filter noise (small specs)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        clean = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        score = cv2.countNonZero(clean)
        return score

    def run(self):
        """Main operational loop"""
        print("OceanPulse Oil Detection Module Started.")
        while True:
            frame = self.capture_sequence()
            if frame is not None:
                score = self.analyze_fluorescence(frame)
                print(f"Sampling complete. Fluorescence Score: {score}")
                
                if score > 1000: # Configurable threshold
                    filename = f"ALARM_spill_{int(time.time())}.jpg"
                    cv2.imwrite(filename, frame)
                    print(f"!!! SPILL ALERT !!! Image saved to {filename}")
            
            # Wait 10 minutes between samples
            time.sleep(600)

if __name__ == "__main__":
    detector = OilDetector()
    detector.run()
