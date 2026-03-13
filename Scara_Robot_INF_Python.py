import serial
import time

PORT = "COM3"
BAUD = 115200

def read_r_line(ser, timeout_s=3.0) -> str:
    end = time.time() + timeout_s
    while time.time() < end:
        line = ser.readline()
        if not line:
            continue
        text = line.decode(errors="ignore").strip()
        if text:
            print("RX:", text)
            if text.startswith("R:"):
                return text
    return ""

def ask(ser, cmd: str, timeout_s=3.0) -> str:
    ser.reset_input_buffer()
    ser.write((cmd.strip() + "\n").encode("utf-8"))
    ser.flush()
    return read_r_line(ser, timeout_s=timeout_s)

with serial.Serial(PORT, BAUD, timeout=0.2) as ser:
    time.sleep(2.0)

    if ask(ser, "SYNC") != "R:READY":
        print("Not ready")
        raise SystemExit

    print("Move 200 steps forward")
    print(ask(ser, "XSTEP 200"))
    print(read_r_line(ser, timeout_s=5.0))

    time.sleep(0.5)

    print("Move 200 steps backward")
    print(ask(ser, "XSTEP 200 -1"))
    print(read_r_line(ser, timeout_s=5.0))

print("Done.")