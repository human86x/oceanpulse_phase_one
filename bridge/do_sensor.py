"""Optical Dissolved Oxygen Sensor — RS485 Modbus RTU driver.

Datasheet (DFRobot-distributed Chinese optical DO sensor, sea-water version):
  - Default baud: 4800 bps, 8N1, no parity, 1 stop bit
  - Default slave address: 0x01
  - Function code 0x03 (read holding registers) / 0x04 also accepted
  - Register map (each value is a 32-bit IEEE 754 float, big-endian, 2 regs):
       0x0000-0x0001  Dissolved Oxygen Saturation  (1.0 = 100%)
       0x0002-0x0003  Dissolved Oxygen Concentration (mg/L)
       0x0004-0x0005  Temperature (°C)
  - Configuration registers (function 0x06/0x10 to write):
       0x1010  Calibration (write 0x0001 = zero point, 0x0002 = 100% sat)
       0x1020  Salinity setting (default 30 for seawater version)
       0x1022  Atmospheric pressure × 100 (default 10133 = 101.33 kPa)
       0x07D0  Device address (1-254)
       0x07D1  Baud rate index (0=2400, 1=4800, 2=9600, 3=19200, ...)

A single read of 6 registers (12 data bytes) returns all three values.
"""
import logging
import struct
import time

import serial

logger = logging.getLogger(__name__)


def _crc16(data: bytes) -> bytes:
    """Modbus CRC-16. Returns 2 bytes, low-byte-first (Modbus on-wire order)."""
    crc = 0xFFFF
    for b in data:
        crc ^= b
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return bytes([crc & 0xFF, (crc >> 8) & 0xFF])


class DOSensor:
    def __init__(self, port: str = "/dev/op-do", baud: int = 4800,
                 addr: int = 0x01, timeout: float = 1.5):
        self.port = port
        self.baud = baud
        self.addr = addr
        self.timeout = timeout
        self._ser = None

    def _open(self) -> bool:
        if self._ser is not None:
            return True
        try:
            self._ser = serial.Serial(
                self.port, self.baud,
                parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS, timeout=self.timeout,
            )
            return True
        except Exception as e:
            logger.error("DO sensor open %s failed: %s", self.port, e)
            self._ser = None
            return False

    def close(self):
        if self._ser is not None:
            try: self._ser.close()
            except Exception: pass
        self._ser = None

    def _transact(self, frame: bytes, expected_len: int) -> bytes | None:
        if not self._open():
            return None
        try:
            self._ser.reset_input_buffer()
            self._ser.write(frame + _crc16(frame))
            # Modbus RTU: response trickles in at ~baud — read expected_len with timeout.
            buf = bytearray()
            deadline = time.time() + self.timeout
            while len(buf) < expected_len and time.time() < deadline:
                chunk = self._ser.read(expected_len - len(buf))
                if chunk:
                    buf.extend(chunk)
                else:
                    break
            return bytes(buf) if buf else None
        except Exception as e:
            logger.error("DO sensor IO error: %s", e)
            self.close()
            return None

    def read_all(self) -> dict | None:
        """Read DO saturation, concentration, and temperature in one transaction.
        Returns dict with keys do_sat (%), do_mgL (mg/L), water_temp (°C), or None on failure.
        """
        # 6 holding registers starting at 0x0000 — three 32-bit big-endian floats.
        frame = struct.pack(">BBHH", self.addr, 0x03, 0x0000, 0x0006)
        # Expected response: addr(1) + func(1) + bytecount(1) + 12 data + CRC(2) = 17 bytes.
        resp = self._transact(frame, 17)
        if not resp or len(resp) < 17:
            logger.debug("DO sensor: short response (%d bytes)", len(resp) if resp else 0)
            return None

        if resp[0] != self.addr or resp[1] != 0x03 or resp[2] != 12:
            logger.warning("DO sensor: bad header %s", resp[:3].hex())
            return None

        # Verify CRC.
        body, crc = resp[:-2], resp[-2:]
        if _crc16(body) != crc:
            logger.warning("DO sensor: CRC mismatch")
            return None

        data = resp[3:-2]  # 12 bytes = 3 floats
        do_sat, do_mgL, temp = struct.unpack(">fff", data)
        return {
            "do_sat": round(do_sat * 100.0, 2),   # spec says 1.0 = 100%
            "do_mgL": round(do_mgL, 3),
            "water_temp": round(temp, 2),
        }

    def calibrate_zero(self) -> bool:
        """Write 0x0001 to register 0x1010 — call once after probe stabilises in
        the 5% sodium-sulfite zero-oxygen solution."""
        return self._write_register(0x1010, 0x0001)

    def calibrate_saturation(self) -> bool:
        """Write 0x0002 to register 0x1010 — call once after probe stabilises
        ~1cm above water-saturated air."""
        return self._write_register(0x1010, 0x0002)

    # -- SPEC-034 config getters/setters --------------------------------------

    def get_salinity_ppt(self) -> int | None:
        """Read register 0x1020 (salinity in ‰). Returns int or None on failure."""
        return self._read_uint16_register(0x1020)

    def set_salinity_ppt(self, ppt: int) -> bool:
        """Write 0x1020 with salinity in ‰. Range 0..255 in practice; sensor
        clamps. Seawater factory default is 30."""
        if not 0 <= ppt <= 255:
            return False
        return self._write_register(0x1020, ppt)

    def get_pressure_kpa_x100(self) -> int | None:
        """Read register 0x1022 (atmospheric pressure × 100, kPa). 10133 = 101.33 kPa."""
        return self._read_uint16_register(0x1022)

    def set_pressure_kpa_x100(self, val: int) -> bool:
        """Write 0x1022 with pressure × 100. Sea-level default 10133."""
        if not 0 <= val <= 65535:
            return False
        return self._write_register(0x1022, val)

    def get_addr(self) -> int | None:
        """Read configured Modbus address from register 0x07D0."""
        return self._read_uint16_register(0x07D0)

    def get_baud_index(self) -> int | None:
        """Read baud-rate index from register 0x07D1.
        Mapping: 0=2400, 1=4800, 2=9600, 3=19200, 4=38400, 5=57600, 6=115200."""
        return self._read_uint16_register(0x07D1)

    # -- Modbus primitives ----------------------------------------------------

    def _write_register(self, reg: int, value: int) -> bool:
        # _transact appends CRC internally — pass 6-byte frame.
        frame = struct.pack(">BBHH", self.addr, 0x06, reg, value)
        resp = self._transact(frame, 8)
        # Response echoes the request bytes + 2-byte CRC; check the first 6.
        return resp is not None and resp[:6] == frame

    def _read_uint16_register(self, reg: int) -> int | None:
        """Function 0x03 read of a single 16-bit register."""
        frame = struct.pack(">BBHH", self.addr, 0x03, reg, 0x0001)
        resp = self._transact(frame, 7)  # addr+func+bc+2data+crc(2) = 7
        if not resp or len(resp) < 7:
            return None
        if resp[0] != self.addr or resp[1] != 0x03 or resp[2] != 2:
            return None
        body, crc = resp[:-2], resp[-2:]
        if _crc16(body) != crc:
            return None
        return (resp[3] << 8) | resp[4]
