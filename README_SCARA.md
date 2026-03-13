
# SCARA Robot Control Project

This project implements a SCARA robot motion controller using:

- Arduino Uno
- CNC Shield V3
- A4988 stepper drivers
- Python control application
- Serial communication

The system allows manual testing of stepper motors and will later support coordinated multi-axis motion.

---

## Project Architecture

Python Controller (main.py)
        ↓ Serial USB
Arduino Firmware (PlatformIO / C++)
        ↓
CNC Shield V3
        ↓
A4988 Stepper Drivers
        ↓
Stepper Motors (X, Y, Z, A)

---

## Project Folder Structure

C:\projectPython\Scara_Robot

│
├── firmware\
│   └── scara-fw\
│       └── scara-fw\
│           ├── src\
│           │   └── main.cpp
│           ├── include\
│           ├── lib\
│           ├── test\
│           ├── extra\
│           ├── .pio\
│           └── platformio.ini
│
├── main.py
├── README.md
└── ARCHITECTURE.md

---

## Hardware

Controller:
Arduino Uno

Motion Driver:
CNC Shield V3

Stepper Drivers:
A4988

Motors:
X Axis
Y Axis
Z Axis
A Axis

Power Supply:
12–36V motor supply

Safety:
Emergency Stop Button

---

## Pin Mapping (CNC Shield V3)

| Axis | STEP | DIR |
|-----|------|------|
| X | D2 | D5 |
| Y | D3 | D6 |
| Z | D4 | D7 |
| A | D12 | D13 |

Enable Pin

EN → D8

Emergency Stop

ESTOP → A0

---

## Communication Protocol

Serial Speed:
115200 baud

Commands are newline terminated.

Example command:

XSTEP 200 300

Command format:

AXISSTEP <steps> <speed> [dir]

Examples:

XSTEP 200 300
YSTEP 500 400 -1

Where:
steps = number of step pulses
speed = steps per second
dir = direction (optional)
1 = forward
-1 = reverse

---

## Supported Commands

SYNC
ENA 1
ENA 0
CLR

Axis movement commands:

XSTEP
YSTEP
ZSTEP
ASTEP

---

## Safety System

When the emergency stop button is pressed:

Drivers are disabled
Motion stops immediately
Firmware reports:

R:ESTOP

To clear:

CLR

---

## Build Firmware

Open firmware folder in VSCode:

C:\projectPython\Scara_Robot\firmware\scara-fw\scara-fw

Build with PlatformIO.

---

## Run Python Controller

python main.py

---

## Project Status

✔ Serial communication working
✔ Single axis motion control
✔ Multi-axis firmware structure
✔ Emergency stop protection

Next steps:

Parallel multi-axis movement
Motion planner
SCARA kinematics
Trajectory generation
