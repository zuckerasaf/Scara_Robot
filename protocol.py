import time

def read_r_line(link, timeout_s: float = 3.0) -> str:
    end = time.time() + timeout_s
    while time.time() < end:
        text = link.read_line()
        if not text:
            continue
        print("RX:", text)
        if text.startswith("R:"):
            return text
    return ""

def ask(link, cmd: str, timeout_s: float = 3.0) -> str:
    link.clear_input()
    link.write_line(cmd)
    return read_r_line(link, timeout_s=timeout_s)