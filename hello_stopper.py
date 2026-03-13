import serial
import time

PORT = "COM3"
BAUD = 115200


def read_r_line(ser, timeout_s=3.0):
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


def ask(ser, cmd, timeout_s=3.0):
    ser.reset_input_buffer()
    ser.write((cmd.strip() + "\n").encode())
    ser.flush()
    return read_r_line(ser, timeout_s)


def main():
    with serial.Serial(PORT, BAUD, timeout=0.2) as ser:

        time.sleep(2.0)

        if ask(ser, "SYNC") != "R:READY":
            print("Not ready")
            return

        ask(ser, "ENA 1")
        ask(ser, "XSTEP 1000")
        read_r_line(ser, 5.0)
        ask(ser, "XSTEP 1000 -1")
        read_r_line(ser, 5.0)
        ask(ser, "ENA 0")

    print("Done.")


if __name__ == "__main__":
    main()