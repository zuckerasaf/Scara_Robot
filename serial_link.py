import time
import serial

class SerialLink:
    def __init__(self, port: str, baud: int, timeout: float = 0.2):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.ser = None

    def open(self):
        self.ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        time.sleep(2.0)  # Uno reset on open
        return self

    def close(self):
        if self.ser:
            self.ser.close()
            self.ser = None

    def __enter__(self):
        return self.open()

    def __exit__(self, exc_type, exc, tb):
        self.close()

    def write_line(self, s: str):
        self.ser.write((s.strip() + "\n").encode("utf-8"))
        self.ser.flush()

    def read_line(self) -> str:
        b = self.ser.readline()
        return b.decode(errors="ignore").strip() if b else ""

    def clear_input(self):
        self.ser.reset_input_buffer()

