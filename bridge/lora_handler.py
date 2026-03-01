import time
import sys
import logging
import threading

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("LoRa")

# Try to import meshtastic, handle if missing (for dev environments without the lib)
try:
    import meshtastic.serial_interface
    from pubsub import pub
    HAS_MESHTASTIC = True
except ImportError:
    HAS_MESHTASTIC = False
    logger.warning("Meshtastic library not found. LoRa features will be SIMULATED.")

class LoraHandler:
    """
    Handles LoRa communication via Meshtastic devices or LoRa-E5 AT firmware.
    Supports real hardware and simulation mode.
    """
    def __init__(self, port='/dev/ttyUSB0', baud=9600, mode='AT'):
        self.port = port
        self.baud = baud
        self.mode = mode # 'MESHTASTIC' or 'AT'
        self.interface = None
        self.ser = None
        self.connected = False
        self.serial_lock = threading.Lock()
        self.tx_in_progress = False

    def connect(self):
        """Establish connection to the LoRa device."""
        if self.mode == 'MESHTASTIC':
            if not HAS_MESHTASTIC:
                logger.info(f"[SIM] Connected to Meshtastic on {self.port}")
                self.connected = True
                return True

            try:
                self.interface = meshtastic.serial_interface.SerialInterface(self.port)
                pub.subscribe(self._on_receive, "meshtastic.receive")
                self.connected = True
                logger.info(f"Connected to Meshtastic on {self.port}")
                return True
            except Exception as e:
                logger.error(f"Failed to connect to Meshtastic on {self.port}: {e}")
                self.connected = False
                return False
        
        elif self.mode == 'AT':
            try:
                import serial
                self.ser = serial.Serial(self.port, self.baud, timeout=2)
                # Wake up module and verify AT response (retry up to 3 times)
                res = ""
                for attempt in range(3):
                    self.ser.reset_input_buffer()
                    self.ser.write(b"AT\r\n")
                    time.sleep(0.5)
                    res = self.ser.read(1024).decode(errors='ignore')
                    if "+AT: OK" in res:
                        break
                    logger.info(f"AT attempt {attempt+1}/3 - no response, retrying...")
                    time.sleep(1)
                if "+AT: OK" in res:
                    logger.info(f"Connected to LoRa-E5 AT on {self.port} at {self.baud}")
                    # Basic setup for P2P
                    self.ser.write(b"AT+MODE=TEST\r\n")
                    time.sleep(0.3)
                    self.ser.read(1024)  # drain response
                    # Use comma syntax for RFCFG (defaults from class constants)
                    rfcfg = (f"AT+TEST=RFCFG,{self.DEFAULT_FREQ},SF{self.DEFAULT_SF},"
                             f"{self.DEFAULT_BW},{self.DEFAULT_TXPR},{self.DEFAULT_RXPR},"
                             f"{self.DEFAULT_POWER},ON,OFF,OFF")
                    self.ser.write(f"{rfcfg}\r\n".encode())
                    time.sleep(0.3)
                    self.ser.read(1024)  # drain response
                    self.connected = True
                    return True
                else:
                    logger.error(f"No AT response from {self.port} after 3 attempts")
                    self.connected = False
                    return False
            except Exception as e:
                logger.error(f"Failed to connect to LoRa-E5 AT on {self.port}: {e}")
                self.connected = False
                return False

    # Default RFCFG values (EU868, SF12, 125kHz BW)
    DEFAULT_FREQ = 868
    DEFAULT_SF = 12
    DEFAULT_BW = 125
    DEFAULT_TXPR = 12
    DEFAULT_RXPR = 15
    DEFAULT_POWER = 14

    def configure(self, freq=None, sf=None):
        """Reconfigure LoRa radio parameters at runtime (AT mode only).

        Args:
            freq: Frequency in MHz (e.g. 868, 915). None keeps current.
            sf: Spreading factor 7-12 (int or string like 'SF10'). None keeps current.

        Returns:
            dict with status and applied config, or error.
        """
        if self.mode != 'AT':
            return {"status": "error", "message": "configure() only supported in AT mode"}
        if not self.connected or not self.ser:
            return {"status": "error", "message": "LoRa not connected"}

        # Parse SF from string like "SF10" or int 10
        if sf is not None:
            if isinstance(sf, str) and sf.upper().startswith("SF"):
                sf = int(sf[2:])
            sf = int(sf)
            if sf < 7 or sf > 12:
                return {"status": "error", "message": f"SF must be 7-12, got {sf}"}

        use_freq = freq if freq is not None else self.DEFAULT_FREQ
        use_sf = sf if sf is not None else self.DEFAULT_SF

        cmd = (f"AT+TEST=RFCFG,{use_freq},SF{use_sf},{self.DEFAULT_BW},"
               f"{self.DEFAULT_TXPR},{self.DEFAULT_RXPR},{self.DEFAULT_POWER},ON,OFF,OFF")

        try:
            with self.serial_lock:
                self.ser.reset_input_buffer()
                self.ser.write(f"{cmd}\r\n".encode())
                time.sleep(0.5)
                res = self.ser.read(self.ser.in_waiting or 1024).decode(errors='ignore')

                if "RFCFG" in res or "OK" in res:
                    logger.info(f"LoRa reconfigured: {use_freq}MHz SF{use_sf}")
                    # Resume RX after config change
                    self.ser.write(b"AT+TEST=RXLRPKT\r\n")
                    time.sleep(0.3)
                    self.ser.read(self.ser.in_waiting or 1024)
                    return {"status": "success", "freq": use_freq, "sf": use_sf}
                else:
                    logger.warning(f"RFCFG response unexpected: {repr(res)}")
                    return {"status": "error", "message": f"Unexpected response: {res.strip()}"}
        except Exception as e:
            logger.error(f"configure() failed: {e}")
            return {"status": "error", "message": str(e)}

    def send_text(self, text):
        """Send a text message over LoRa."""
        if not self.connected:
            logger.error("Cannot send: LoRa interface not connected")
            return False

        if self.mode == 'MESHTASTIC':
            if not HAS_MESHTASTIC:
                logger.info(f"[SIM] TX Packet: {text}")
                return True
            try:
                self.interface.sendText(text)
                logger.info(f"TX Packet: {text}")
                return True
            except Exception as e:
                logger.error(f"Error sending LoRa packet: {e}")
                return False
        
        elif self.mode == 'AT':
            try:
                with self.serial_lock:
                    self.tx_in_progress = True
                    try:
                        time.sleep(0.2)  # Let listen thread yield
                        self.ser.reset_input_buffer()

                        # Note: Do NOT re-send AT+MODE=TEST here.
                        # It resets RFCFG to defaults, causing TX on wrong
                        # radio parameters. Module is already in TEST mode
                        # from connect().

                        # Convert text to hex and send
                        hex_str = text.encode().hex()
                        cmd = f'AT+TEST=TXLRPKT,"{hex_str}"'
                        self.ser.reset_input_buffer()
                        self.ser.write(f"{cmd}\r\n".encode())

                        # Wait for TX DONE (SF12 takes ~2s)
                        time.sleep(2.5)
                        res = self.ser.read(self.ser.in_waiting or 4096).decode(errors='ignore')
                        success = "TX DONE" in res

                        # Resume RX mode
                        self.ser.reset_input_buffer()
                        self.ser.write(b"AT+TEST=RXLRPKT\r\n")
                        time.sleep(0.3)
                        self.ser.read(self.ser.in_waiting or 1024)  # drain

                        if success:
                            logger.info(f"TX AT Packet: {text} (HEX: {hex_str})")
                        else:
                            logger.warning(f"TX AT Packet may have failed: {repr(res)}")
                        return success
                    finally:
                        self.tx_in_progress = False
            except Exception as e:
                logger.error(f"Error sending AT packet: {e}")
                return False

    def broadcast(self, message):
        """Alias for send_text to broadcast a message."""
        return self.send_text(message)

    def listen(self, callback=None):
        """Listen for incoming LoRa packets (AT mode)."""
        if self.mode != 'AT' or not self.ser:
            logger.error("Listen mode only supported for AT firmware")
            return

        # Start continuous receive
        self.ser.write(b"AT+TEST=RXLRPKT\r\n")
        logger.info("LoRa-E5 entering RX mode")

        try:
            while True:
                if self.tx_in_progress:
                    time.sleep(0.1)
                    continue
                
                if self.ser.in_waiting == 0:
                    time.sleep(0.05)
                    continue
                    
                line = self.ser.readline().decode(errors='ignore').strip()
                if line:
                    if "+TEST: RX" in line:
                        import re
                        match = re.search(r'RX "([0-9A-Fa-f]+)"', line)
                        if match:
                            hex_data = match.group(1)
                            payload = bytes.fromhex(hex_data).decode(errors='ignore')
                            logger.info(f"RX AT Packet: {payload}")
                            if callback:
                                callback(payload)
        except Exception as e:
            logger.error(f"LoRa listen error: {e}")

    def close(self):
        """Close the connection."""
        if self.interface:
            self.interface.close()
        self.connected = False
        logger.info("LoRa connection closed")

    def _on_receive(self, packet, interface):
        """Internal callback for Meshtastic events"""
        try:
            if 'decoded' in packet and 'text' in packet['decoded']:
                text = packet['decoded']['text']
                logger.info(f"RX Packet: {text}")
                # TODO: Implement Command Parsing (SPEC-002/FIRMWARE_SPEC)
                # C:TARGET=x;ACT=x
        except KeyError:
            pass

if __name__ == "__main__":
    # CLI Test
    if len(sys.argv) > 1:
        port = sys.argv[1]
    else:
        port = '/dev/ttyUSB0'
    
    handler = LoraHandler(port)
    if handler.connect():
        handler.broadcast("M:TEST=1;STATUS=OK")
        print("Waiting for messages (Ctrl+C to stop)...")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Stopping...")
        finally:
            handler.close()
