
# SCARA Robot Firmware Architecture

This document describes the internal design of the SCARA robot motion controller.

---

## System Overview

The control system is divided into two major components:

1. Python Control Layer
2. Arduino Motion Controller

Python handles:

- user input
- command parsing
- serial communication

Arduino handles:

- real-time motor control
- safety logic
- motion execution

---

## Communication Flow

Python → Serial → Arduino

Commands are ASCII text messages.

Example:

XSTEP 1000 300

The Arduino parses the command and executes the requested movement.

---

## Motion Engine (Current Version)

The current motion engine uses a simple blocking loop.

Steps are generated using:

digitalWrite(stepPin, HIGH)
delayMicroseconds(5)
digitalWrite(stepPin, LOW)

Speed control is implemented using delayMicroseconds between steps.

This design is simple and reliable but does not support true simultaneous multi-axis motion.

---

## Emergency Stop System

Hardware button connected to:

A0 (ESTOP_PIN)

Logic:

Button Pressed → LOW
Button Released → HIGH

Firmware behavior:

1. Stop motion immediately
2. Disable motor drivers
3. Send response to Python

R:ESTOP

System enters a latched state until cleared with:

CLR

---

## Driver Enable System

All stepper drivers share one enable pin.

EN_PIN = D8

LOW → drivers enabled
HIGH → drivers disabled

---

## Motion Function

Generic motion function:

moveStepsAxis(stepPin, dirPin, steps, direction, speed)

This allows reuse of the same logic for:

X axis
Y axis
Z axis
A axis

---

## Current Limitations

The current firmware has several limitations:

- Movement is blocking
- Only one axis moves at a time
- No acceleration control
- No trajectory planning

---

## Planned Improvements

Next development stages:

Level 1:
Interleaved stepping for simple multi-axis motion

Level 2:
Timer-based step generation

Level 3:
Acceleration profiles

Level 4:
SCARA kinematics

Level 5:
Full motion planner

---

## Long Term Vision

Eventually the firmware will support:

Coordinated multi-axis motion
SCARA inverse kinematics
Smooth acceleration
Path planning
Robot workspace control
