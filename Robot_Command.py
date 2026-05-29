from os import link
import time

from protocol import ask
from serial_link import SerialLink
from motions import handshake, enable, xstep, wait_done

PORT = "COM3"
BAUD = 115200

def Robot_command (user_input, link, log=None):

    log(f"[GO] Executing Robot command")

    if not user_input:
        return "No command entered"

    cmd = user_input.lower()
    parts = cmd.split()
    # Quit
    if cmd in ("q", "quit", "exit"):
        return f"Quit command received"
       
    # test the ESTOP button
    if cmd in ("estop?", "estop"):
        resp = ask(link, "ESTOP?")
        return f"{resp}"

    # test the X stopper switch
    if cmd in ("xstop?", "xstop"):
        resp = ask(link, "XSTOP?")
        return f"{resp}"

    # test the Y stopper switch
    if cmd in ("ystop?", "ystop"):
        resp = ask(link, "YSTOP?")
        return f"{resp}"

    # test the Z stopper switch
    if cmd in ("zstop?", "zstop"):
        resp = ask(link, "ZSTOP?")
        return f"{resp}"

    # test the A stopper switch
    if cmd in ("astop?", "astop"):
        resp = ask(link, "ASTOP?")
        return f"{resp}"

    # Test A direction pin
    if cmd in ("adir?", "adir"):
        print("Testing A_DIR pin (will toggle 5 times)...")
        resp = ask(link, "ADIR?")
        return f"{resp}"

    # Enable / disable technician mode
    if cmd.startswith("tech"):
        if len(parts) != 2 or parts[1] not in ("0", "1"):
            return("Use: TECH 1 or TECH 0")
        return(ask(link, f"TECH {parts[1]}"))
                    
    # Clear E-stop
    if cmd in ("clr", "clear"):
        resp = ask(link, "CLR")
        string_temp= resp

        if resp == "R:OK estop_cleared":
            print("Re-enabling drivers...")
            resp = ask(link, "ENA 1")
            string_temp += "\t" + resp
        return(string_temp)


    # Enable / disable drivers
    if cmd.startswith("ena"):
        if len(parts) != 2 or parts[1] not in ("0", "1"):
            return("Use: ENA 1 or ENA 0")
        return(ask(link, f"ENA {parts[1]}"))
                    
                
    # SYNC
    if cmd == "sync":
        return(ask(link, "SYNC"))
                
    # Gripper control
    if cmd.startswith("grip"):
        if len(parts) != 2:
            return("Format: grip <angle>   ex: grip 90   (0-180°)")
        try:
            angle = int(parts[1])
            if angle < 0 or angle > 180:
                return("Angle must be between 0 and 180")
            return(ask(link, f"GRIP {angle}"))
        except ValueError:
            return("Invalid angle number")

    # Coordinated XZ move: xzstep <x_steps> <z_steps> <x_speed> <z_speed> [x_dir] [z_dir]
    if parts[0] == "xzstep":
        if len(parts) < 5 or len(parts) > 7:
            return("Format: xzstep <x_steps> <z_steps> <x_speed> <z_speed> [x_dir] [z_dir]")
        try:
            x_steps_in = int(parts[1])
            z_steps_in = int(parts[2])
            x_speed = int(parts[3])
            z_speed = int(parts[4])
        except ValueError:
            return("Invalid numbers")
        x_dir = int(parts[5]) if len(parts) >= 6 else (1 if x_steps_in >= 0 else -1)
        z_dir = int(parts[6]) if len(parts) >= 7 else (1 if z_steps_in >= 0 else -1)
        x_steps = abs(x_steps_in)
        z_steps = abs(z_steps_in)
        resp = ask(link, f"XZSTEP {x_steps} {z_steps} {x_speed} {z_speed} {x_dir} {z_dir}")
        if resp == "R:ESTOP":
            return("E-stop triggered. Release button, then type: clr to clear.")
        if resp == "R:XSTOPPER_HIT":
            return("X stopper hit during coordinated move!")
        if resp == "R:ZSTOPPER_HIT":
            return("Z stopper hit during coordinated move!")
        return(f"{resp}")

    # Axis move: <axis> <steps> <speed>
    if len(parts) != 3:
        return("Format: x|y|z|a <steps> <speed_sps>   ex: x 2000 500   or: y -1500 600")
    axis = parts[0].lower()
    try:
        steps_in = int(parts[1])
        speed = int(parts[2])
    except ValueError:
        return("Invalid numbers")
                    

    direction = 1
    steps = steps_in
    if steps_in < 0:
        direction = -1
        steps = abs(steps)

    string_temp =f"Moving {steps} steps at {speed} steps/sec, dir={direction}"
    if axis == "x":
        resp = ask(link, f"XSTEP {steps} {speed} {direction}")
    elif axis == "y":
        resp = ask(link, f"YSTEP {steps} {speed} {direction}")
    elif axis == "z":
        resp = ask(link, f"ZSTEP {steps} {speed} {direction}")
    elif axis == "a":
        resp = ask(link, f"ASTEP {steps} {speed} {direction}")
    else:
        return("Invalid axis, use 'x', 'y', 'z', or 'a'")
           
    if resp == "R:ESTOP":
        return(f"E-stop triggered. Release button, then type: clr to clear.")
                
    if resp == "R:XSTOPPER_HIT":
        return(f"X stopper hit! Move in opposite direction to back away.")
                    
    if resp == "R:ERR xstopper_blocking":
        return(f"X stopper is blocking this direction. Move in opposite direction.")
                
    if resp == "R:YSTOPPER_HIT":
            return(f"Y stopper hit! Move in opposite direction to back away.")
                    
    if resp == "R:ERR ystopper_blocking":
        return(f"Y stopper is blocking this direction. Move in opposite direction.")
                
    if resp == "R:ZSTOPPER_HIT":
        return(f"Z stopper hit! Move in opposite direction to back away.")
                    
    if resp == "R:ERR zstopper_blocking":
        return(f"Z stopper is blocking this direction. Move in opposite direction.")
                
    if resp == "R:ASTOPPER_HIT":
        return(f"A stopper hit! Move in opposite direction to back away.")
                    
    if resp == "R:ERR astopper_blocking":
        return(f"A stopper is blocking this direction. Move in opposite direction.")

    return (f"{resp}")

    #print(wait_done(link, 10))


def main():
    with SerialLink(PORT, BAUD) as link:

        if not handshake(link):
            print("Not ready")
            return

        print("Connected to SCARA controller")
        print("Format: x|y|z|a <steps> <speed_sps>   ex: x 2000 500   or: y -1500 600")
        print("Commands: estop? | xstop? | ystop? | zstop? | astop? | clr | tech 1 | tech 0")
        print("          grip <angle>  (servo gripper 0-180°)")
        print("Type 'q' to quit")
        print()

        enable(link, True)

        try:
            while True:
                user_input = input("Axis Steps Speed> ").strip()
                String_to_print= (Robot_command(user_input, link))
                print(String_to_print)
                if String_to_print == "Quit command received":
                    break

                
        except KeyboardInterrupt:
            print("\nInterrupted by user")

        finally:
            enable(link, False)
            print("Motor disabled")

    print("Disconnected")


if __name__ == "__main__":
    main()