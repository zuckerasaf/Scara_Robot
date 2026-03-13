from protocol import ask, read_r_line

def handshake(link):
    r = ask(link, "SYNC", timeout_s=3.0)
    return r == "R:READY"

def enable(link, on: bool):
    return ask(link, "ENA 1" if on else "ENA 0")

def xstep(link, steps: int, dir: int = 1, speed_sps: int = 800):
    # Arduino expects: XSTEP <steps> <speed_sps> [dir]
    return ask(link, f"XSTEP {steps} {speed_sps} {dir}")

def ystep(link, steps: int, dir: int = 1, speed_sps: int = 800):
    return ask(link, f"YSTEP {steps} {speed_sps} {dir}")

def wait_done(link, timeout_s: float = 10.0):
    return read_r_line(link, timeout_s=timeout_s)