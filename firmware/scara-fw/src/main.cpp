// ============================================================
//  SCARA ROBOT - BASIC X AXIS CONTROLLER
//  PlatformIO + Arduino Uno
//  CNC Shield V3 + A4988
//
//  This firmware:
//    - Receives serial commands from Python
//    - Controls X axis stepper motor
//    - Enables / disables driver
//    - Replies using structured protocol ("R:...")
//
//  Communication speed: 115200 baud
//  Commands (newline terminated):
//    SYNC
//    ENA 1 / ENA 0
//    CLR                        (clear estop latch if button released)
//    ESTOP?                     (query E-stop button state)
//    XSTOP?                     (query X stopper switch state)
//    YSTOP?                     (query Y stopper switch state)
//    ZSTOP?                     (query Z stopper switch state)
//    ASTOP?                     (query A stopper switch state)
//    TECH 1 / TECH 0            (enable/disable technician mode - bypasses stoppers)
//    GRIP <angle>               (set gripper servo angle 0-180)
//    XSTEP <steps> <speed_sps> [dir]
//    YSTEP <steps> <speed_sps> [dir]
//    ZSTEP <steps> <speed_sps> [dir]
//    ASTEP <steps> <speed_sps> [dir]
//    XZSTEP <x_steps> <z_steps> <x_speed_sps> <z_speed_sps> [x_dir] [z_dir]
//
//  speed_sps = steps per second (ex: 800)
//  dir: >=0 forward (default), <0 reverse
// ============================================================

#include <Arduino.h>
#include <Servo.h>



// ============================================================
// PIN DEFINITIONS (CNC Shield V3 mapping for Arduino Uno)
// ============================================================

// X axis STEP pin (one pulse = one microstep) ,direction pin
const int X_STEP_PIN = 2;
const int X_DIR_PIN  = 5;
// Y axis STEP pin, direction pin
const int Y_STEP_PIN = 3;
const int Y_DIR_PIN  = 6;
// Z axis STEP pin, direction pin  
const int Z_STEP_PIN = 4;
const int Z_DIR_PIN  = 7;
// A axis STEP pin, direction pin
// NOTE: Using A5 instead of 13 to avoid onboard LED interference
const int A_STEP_PIN = 12;
const int A_DIR_PIN  = 13;  // Changed from 13 (which has onboard LED)

// Driver enable pin (shared by all axes on shield)
// LOW  = drivers enabled
// HIGH = drivers disabled
const int EN_PIN     = 8;
// Emergency stop pin (Normally open logic Not pressed → HIGH, Pressed → LOW)
const int ESTOP_PIN = A0;
bool estopLatched = false;
// X axis stopper switch (active HIGH: pressed = 1, released = 0)
const int XSTOPPER_PIN = 9;
int xStopperBlockedDir = 0;
// Y axis stopper switch (active HIGH: pressed = 1, released = 0)
const int YSTOPPER_PIN = 10;
int yStopperBlockedDir = 0;
// Z axis stopper switch (A3active HIGH: pressed = 1, released = 0)
const int ZSTOPPER_PIN = 11;
int zStopperBlockedDir = 0;
// A axis stopper switch (active HIGH: pressed = 1, released = 0)
const int ASTOPPER_PIN = A1;
int aStopperBlockedDir = 0;
// Technician mode: bypass stopper checks (for manual recovery)
bool technicianMode = false;
// Servo gripper control (MG996R) - using analog pin A3
const int SERVO_PIN = A3;
Servo gripperServo;
int currentGripperAngle = 90;  // Start at mid position
// Safety limits for speed (steps per second)
const unsigned int MIN_SPS = 50;
const unsigned int MAX_SPS = 2000;
// Acceleration profile: steps/sec² (change per second)
// Conservative: 200 sps² means +200 sps velocity every 1 second
const unsigned int ACCEL_SPS2 = 200;  // Acceleration rate
const unsigned int MIN_ACCEL_SPS = 200;  // Minimum speed during ramp (raised to avoid low-speed resonance)
// ============================================================
// HELPER FUNCTION: reply()
// ============================================================
// Sends structured response back to Python.
// Prefix "R:" allows Python to filter valid responses.
//
void reply(const String& s)
{
    Serial.println("R:" + s);
}
// ============================================================
// HELPER FUNCTION: isEstopActive()
// ============================================================
// Checks if the emergency stop is active.
// Returns true if active, false otherwise.
//
bool isEstopActive() {
  return digitalRead(ESTOP_PIN) == LOW;  // active LOW
}
// ============================================================
// HELPER FUNCTION: isXStopperActive()
// ============================================================
// Checks if the X axis stopper switch is active.
// Returns true if active, false otherwise.
//
bool isXStopperActive() {
  return digitalRead(XSTOPPER_PIN) == HIGH;  // active HIGH (pressed = 1, released = 0)
}
// ============================================================
// HELPER FUNCTION: isYStopperActive()
// ============================================================
// Checks if the Y axis stopper switch is active.
// Returns true if active, false otherwise.
//
bool isYStopperActive() {
  return digitalRead(YSTOPPER_PIN) == HIGH;  // active HIGH (pressed = 1, released = 0)
}
// ============================================================
// HELPER FUNCTION: isZStopperActive()
// ============================================================
// Checks if the Z axis stopper switch is active.
// Returns true if active, false otherwise.
//
bool isZStopperActive() {
  return digitalRead(ZSTOPPER_PIN) == HIGH;  // active HIGH (pressed = 1, released = 0)
}
// ============================================================
// HELPER FUNCTION: isAStopperActive()
// ============================================================
// Checks if the A axis stopper switch is active.
// Returns true if active, false otherwise.
//
bool isAStopperActive() {
  return digitalRead(ASTOPPER_PIN) == HIGH;  // active HIGH (pressed = 1, released = 0)
}
// ============================================================
// HELPER FUNCTION: triggerEstop()
// ============================================================
// Triggers the emergency stop.
// Disables drivers and notifies host.
//
void triggerEstop(const char* axisName = "") {
  estopLatched = true;
  digitalWrite(EN_PIN, HIGH);  // disable drivers
  reply(String("ESTOP axis=") + axisName);
}
// ============================================================
// HELPER FUNCTION: stepPulse()
// ============================================================
// Generates ONE step pulse on STEP pin.
//
// A4988 moves one microstep on LOW->HIGH->LOW transition.
// Minimum pulse width required is ~1–2 microseconds.
// We use 5 microseconds for safety.
//
// parameter stepPin → the STEP pin number to pulse

void stepPulse(int stepPin) {
  digitalWrite(stepPin, HIGH);
  delayMicroseconds(5);        // safe pulse width
  digitalWrite(stepPin, LOW);
}

// ============================================================
// HELPER FUNCTION: spsToDelayUs()
// ============================================================
// Convert steps/sec to delay in microseconds between steps.
// delay_us = 1,000,000 / steps_per_sec
unsigned long spsToDelayUs(unsigned int sps) {
  if (sps < MIN_SPS) sps = MIN_SPS;
  if (sps > MAX_SPS) sps = MAX_SPS;
  return 1000000UL / (unsigned long)sps;
}

// ============================================================
// HELPER FUNCTION: calculateAccelSteps()
// ============================================================
// Calculate steps needed to reach max_speed from min_speed with acceleration.
// Using kinematic formula: v² = u² + 2*a*s
// Rearranged: s = (v² - u²) / (2*a)
//   where a is in steps/sec² but we use a discrete approximation
unsigned long calculateAccelSteps(unsigned int min_sps, unsigned int max_sps, unsigned int accel_sps2) {
  if (accel_sps2 == 0 || max_sps <= min_sps) return 0;
  // Approximate: use (max - min) / accel_sps2 * 50 as a heuristic
  // More precise would need floating point
  unsigned long steps = ((unsigned long)(max_sps - min_sps) * 50) / accel_sps2;
  return steps;
}


// ============================================================
// FUNCTION: moveStepsX()
// ============================================================
// Moves the motor a given number of steps in selected direction.
//
// Parameters:
//   steps → number of steps to move
//   dir   → >=0 forward, <0 reverse
//   speedSps → speed in steps per second
//
// NOTE:
//   This function BLOCKS until movement is finished.
//   CPU does nothing else during motion.
//
//

bool moveStepsAxis(const char* axisName, int stepPin, int dirPin, long steps, int dir, unsigned int speedSps) {
  
  // Determine if we should check stoppers during this movement
  bool checkXStopper = true;
  bool checkYStopper = true;
  bool checkZStopper = true;
  bool checkAStopper = true;
  int moveDir = (dir >= 0) ? 1 : -1;
  
  // Special handling for X axis with stopper
  if (axisName[0] == 'X') {
    // If technician mode is enabled, bypass all stopper checks
    if (technicianMode) {
      checkXStopper = false;
    } else if (isXStopperActive()) {
      // Stopper is currently pressed
      if (xStopperBlockedDir != 0) {
        // We know which direction is blocked
        if (moveDir == xStopperBlockedDir) {
          // Trying to move in the blocked direction
          reply("ERR xstopper_blocking");
          return false;
        } else {
          // Moving in opposite direction - allow backing away without checking
          checkXStopper = false;
        }
      }
      // If xStopperBlockedDir == 0, we don't know the direction yet
      // Allow the movement and let the loop detect if it's wrong
    } else {
      // Stopper is not pressed - clear the blocked direction and enable checking
      xStopperBlockedDir = 0;
      checkXStopper = true;
    }
  }
  
  // Special handling for Y axis with stopper
  if (axisName[0] == 'Y') {
    // If technician mode is enabled, bypass all stopper checks
    if (technicianMode) {
      checkYStopper = false;
    } else if (isYStopperActive()) {
      // Stopper is currently pressed
      if (yStopperBlockedDir != 0) {
        // We know which direction is blocked
        if (moveDir == yStopperBlockedDir) {
          // Trying to move in the blocked direction
          reply("ERR ystopper_blocking");
          return false;
        } else {
          // Moving in opposite direction - allow backing away without checking
          checkYStopper = false;
        }
      }
      // If yStopperBlockedDir == 0, we don't know the direction yet
      // Allow the movement and let the loop detect if it's wrong
    } else {
      // Stopper is not pressed - clear the blocked direction and enable checking
      yStopperBlockedDir = 0;
      checkYStopper = true;
    }
  }
  
  // Special handling for Z axis with stopper
  if (axisName[0] == 'Z') {
    // If technician mode is enabled, bypass all stopper checks
    if (technicianMode) {
      checkZStopper = false;
    } else if (isZStopperActive()) {
      // Stopper is currently pressed
      if (zStopperBlockedDir != 0) {
        // We know which direction is blocked
        if (moveDir == zStopperBlockedDir) {
          // Trying to move in the blocked direction
          reply("ERR zstopper_blocking");
          return false;
        } else {
          // Moving in opposite direction - allow backing away without checking
          checkZStopper = false;
        }
      }
      // If zStopperBlockedDir == 0, we don't know the direction yet
      // Allow the movement and let the loop detect if it's wrong
    } else {
      // Stopper is not pressed - clear the blocked direction and enable checking
      zStopperBlockedDir = 0;
      checkZStopper = true;
    }
  }
  
  // Special handling for A axis with stopper
  if (axisName[0] == 'A') {
    // If technician mode is enabled, bypass all stopper checks
    if (technicianMode) {
      checkAStopper = false;
    } else if (isAStopperActive()) {
      // Stopper is currently pressed
      if (aStopperBlockedDir != 0) {
        // We know which direction is blocked
        if (moveDir == aStopperBlockedDir) {
          // Trying to move in the blocked direction
          reply("ERR astopper_blocking");
          return false;
        } else {
          // Moving in opposite direction - allow backing away without checking
          checkAStopper = false;
        }
      }
      // If aStopperBlockedDir == 0, we don't know the direction yet
      // Allow the movement and let the loop detect if it's wrong
    } else {
      // Stopper is not pressed - clear the blocked direction and enable checking
      aStopperBlockedDir = 0;
      checkAStopper = true;
    }
  }
  
  // Set direction pin (inverted for A axis to correct rotation direction)
  if (axisName[0] == 'A') {
    digitalWrite(dirPin, (dir >= 0) ? LOW : HIGH);  // Inverted for A axis
  } else {
    digitalWrite(dirPin, (dir >= 0) ? HIGH : LOW);  // Normal for X, Y, Z
  }

  // Choose a safe ramp start speed (never above target speed).
  unsigned int start_sps = (speedSps < MIN_ACCEL_SPS) ? speedSps : MIN_ACCEL_SPS;

  // Calculate trapezoidal acceleration profile
  unsigned long accel_steps = calculateAccelSteps(start_sps, speedSps, ACCEL_SPS2);
  unsigned long decel_start = (steps > 2 * accel_steps) ? (steps - accel_steps) : (steps / 2);
  unsigned long cruise_start = accel_steps;
  
  // If move is very short, triangle profile: only accel then decel, no cruise
  if (steps <= 2 * accel_steps) {
    cruise_start = steps / 2;
    decel_start = cruise_start;
  }

  unsigned long delayUs = spsToDelayUs(speedSps);
  unsigned int current_sps = start_sps;  // Start at ramp start speed

  for (long i = 0; i < steps; i++) {
    if (isEstopActive()) {
      triggerEstop(axisName);
     
      return false;
    }
    
    // Check X stopper if moving X axis (and checking is enabled)
    if (axisName[0] == 'X' && checkXStopper && isXStopperActive()) {
      // Record which direction hit the stopper
      xStopperBlockedDir = moveDir;
      reply("XSTOPPER_HIT");
      return false;
    }
    
    // Check Y stopper if moving Y axis (and checking is enabled)
    if (axisName[0] == 'Y' && checkYStopper && isYStopperActive()) {
      // Record which direction hit the stopper
      yStopperBlockedDir = moveDir;
      reply("YSTOPPER_HIT");
      return false;
    }
    
    // Check Z stopper if moving Z axis (and checking is enabled)
    if (axisName[0] == 'Z' && checkZStopper && isZStopperActive()) {
      // Record which direction hit the stopper
      zStopperBlockedDir = moveDir;
      reply("ZSTOPPER_HIT");
      return false;
    }
    
    // Check A stopper if moving A axis (and checking is enabled)
    if (axisName[0] == 'A' && checkAStopper && isAStopperActive()) {
      // Record which direction hit the stopper
      aStopperBlockedDir = moveDir;
      reply("ASTOPPER_HIT");
      return false;
    }
    
    // Update speed based on phase
    if (cruise_start > 0 && i < cruise_start) {
      // Acceleration phase: increase speed smoothly
      current_sps = start_sps + (unsigned int)(((long)(speedSps - start_sps) * i) / cruise_start);
      delayUs = spsToDelayUs(current_sps);
    } else if (i < decel_start) {
      // Cruise phase: maintain max speed
      current_sps = speedSps;
      delayUs = spsToDelayUs(speedSps);
    } else {
      // Deceleration phase: decrease speed smoothly
      long remaining = steps - i;
      long decel_distance = steps - decel_start;
      if (decel_distance > 0) {
        current_sps = start_sps + (unsigned int)(((long)(speedSps - start_sps) * remaining) / decel_distance);
      } else {
        current_sps = speedSps;
      }
      delayUs = spsToDelayUs(current_sps);
    }
    
    stepPulse(stepPin);
    delayMicroseconds(delayUs);
   
  }
  return true;
}

// ============================================================
// FUNCTION: moveStepsXZCoordinated()
// ============================================================
// Moves X and Z axes together in one coordinated loop.
// This keeps both axes active at the same time instead of sequential moves.
//
bool moveStepsXZCoordinated(long xSteps, int xDir, unsigned int xSpeedSps,
                            long zSteps, int zDir, unsigned int zSpeedSps) {
  bool checkXStopper = true;
  bool checkZStopper = true;
  int xMoveDir = (xDir >= 0) ? 1 : -1;
  int zMoveDir = (zDir >= 0) ? 1 : -1;

  // X stopper pre-check behavior matches single-axis movement.
  if (technicianMode) {
    checkXStopper = false;
  } else if (isXStopperActive()) {
    if (xStopperBlockedDir != 0) {
      if (xMoveDir == xStopperBlockedDir) {
        reply("ERR xstopper_blocking");
        return false;
      } else {
        checkXStopper = false;
      }
    }
  } else {
    xStopperBlockedDir = 0;
    checkXStopper = true;
  }

  // Z stopper pre-check behavior matches single-axis movement.
  if (technicianMode) {
    checkZStopper = false;
  } else if (isZStopperActive()) {
    if (zStopperBlockedDir != 0) {
      if (zMoveDir == zStopperBlockedDir) {
        reply("ERR zstopper_blocking");
        return false;
      } else {
        checkZStopper = false;
      }
    }
  } else {
    zStopperBlockedDir = 0;
    checkZStopper = true;
  }

  // Set directions for X and Z.
  digitalWrite(X_DIR_PIN, (xDir >= 0) ? HIGH : LOW);
  digitalWrite(Z_DIR_PIN, (zDir >= 0) ? HIGH : LOW);

  // Per-axis ramp setup for coordinated motion.
  unsigned int xStartSps = (xSpeedSps < MIN_ACCEL_SPS) ? xSpeedSps : MIN_ACCEL_SPS;
  unsigned int zStartSps = (zSpeedSps < MIN_ACCEL_SPS) ? zSpeedSps : MIN_ACCEL_SPS;

  unsigned long xAccelSteps = calculateAccelSteps(xStartSps, xSpeedSps, ACCEL_SPS2);
  unsigned long zAccelSteps = calculateAccelSteps(zStartSps, zSpeedSps, ACCEL_SPS2);

  unsigned long xDecelStart = (xSteps > 2 * (long)xAccelSteps) ? (xSteps - xAccelSteps) : (xSteps / 2);
  unsigned long zDecelStart = (zSteps > 2 * (long)zAccelSteps) ? (zSteps - zAccelSteps) : (zSteps / 2);

  unsigned long xCruiseStart = xAccelSteps;
  unsigned long zCruiseStart = zAccelSteps;

  if (xSteps <= 2 * (long)xAccelSteps) {
    xCruiseStart = xSteps / 2;
    xDecelStart = xCruiseStart;
  }
  if (zSteps <= 2 * (long)zAccelSteps) {
    zCruiseStart = zSteps / 2;
    zDecelStart = zCruiseStart;
  }

  unsigned int xCurrentSps = xStartSps;
  unsigned int zCurrentSps = zStartSps;

  unsigned long xDelayUs = spsToDelayUs(xCurrentSps);
  unsigned long zDelayUs = spsToDelayUs(zCurrentSps);

  unsigned long now = micros();
  unsigned long nextXStepUs = now;
  unsigned long nextZStepUs = now;

  long xDone = 0;
  long zDone = 0;

  while (xDone < xSteps || zDone < zSteps) {
    if (isEstopActive()) {
      triggerEstop("XZ");
      return false;
    }

    if (checkXStopper && isXStopperActive()) {
      xStopperBlockedDir = xMoveDir;
      reply("XSTOPPER_HIT");
      return false;
    }

    if (checkZStopper && isZStopperActive()) {
      zStopperBlockedDir = zMoveDir;
      reply("ZSTOPPER_HIT");
      return false;
    }

    now = micros();
    bool stepped = false;

    if (xDone < xSteps && (long)(now - nextXStepUs) >= 0) {
      // X acceleration profile
      if (xCruiseStart > 0 && xDone < (long)xCruiseStart) {
        xCurrentSps = xStartSps + (unsigned int)(((long)(xSpeedSps - xStartSps) * xDone) / xCruiseStart);
      } else if (xDone < (long)xDecelStart) {
        xCurrentSps = xSpeedSps;
      } else {
        long xRemaining = xSteps - xDone;
        long xDecelDistance = xSteps - (long)xDecelStart;
        if (xDecelDistance > 0) {
          xCurrentSps = xStartSps + (unsigned int)(((long)(xSpeedSps - xStartSps) * xRemaining) / xDecelDistance);
        } else {
          xCurrentSps = xSpeedSps;
        }
      }
      xDelayUs = spsToDelayUs(xCurrentSps);

      stepPulse(X_STEP_PIN);
      xDone++;
      nextXStepUs += xDelayUs;
      stepped = true;
    }

    if (zDone < zSteps && (long)(now - nextZStepUs) >= 0) {
      // Z acceleration profile
      if (zCruiseStart > 0 && zDone < (long)zCruiseStart) {
        zCurrentSps = zStartSps + (unsigned int)(((long)(zSpeedSps - zStartSps) * zDone) / zCruiseStart);
      } else if (zDone < (long)zDecelStart) {
        zCurrentSps = zSpeedSps;
      } else {
        long zRemaining = zSteps - zDone;
        long zDecelDistance = zSteps - (long)zDecelStart;
        if (zDecelDistance > 0) {
          zCurrentSps = zStartSps + (unsigned int)(((long)(zSpeedSps - zStartSps) * zRemaining) / zDecelDistance);
        } else {
          zCurrentSps = zSpeedSps;
        }
      }
      zDelayUs = spsToDelayUs(zCurrentSps);

      stepPulse(Z_STEP_PIN);
      zDone++;
      nextZStepUs += zDelayUs;
      stepped = true;
    }

    if (!stepped) {
      delayMicroseconds(20);
    }
  }

  return true;
}

// ============================================================
// PARSER: parse "steps speed [dir]" from a command line after XSTEP/YSTEP
// Returns true on success; false on parse error (and replies ERR ...)
// ============================================================
bool parseStepsSpeedDir(const String& line, long& stepsOut, unsigned int& speedOut, int& dirOut) {
  // Remove command name (assumes caller used substring(5) already or passes rest)
  String rest = line;
  rest.trim();

  // Expect at least: "<steps> <speed>"
  int sp1 = rest.indexOf(' ');
  if (sp1 < 0) { reply("ERR missing_args"); return false; }

  String stepsStr = rest.substring(0, sp1);
  String after0   = rest.substring(sp1 + 1);
  after0.trim();

  int sp2 = after0.indexOf(' ');
  String speedStr = (sp2 < 0) ? after0 : after0.substring(0, sp2);
  String dirStr   = (sp2 < 0) ? ""     : after0.substring(sp2 + 1);
  dirStr.trim();

  long steps = stepsStr.toInt();
  unsigned int speed = (unsigned int)speedStr.toInt();

  if (steps <= 0) { reply("ERR bad_steps"); return false; }
  if (speed == 0) { reply("ERR bad_speed"); return false; }

  int dir = 1;
  if (dirStr.length() > 0) dir = dirStr.toInt();

  // clamp speed for safety
  if (speed < MIN_SPS) speed = MIN_SPS;
  if (speed > MAX_SPS) speed = MAX_SPS;

  stepsOut = steps;
  speedOut = speed;
  dirOut   = dir;
  return true;
}

// ============================================================
// PARSER: parse "x_steps z_steps x_speed z_speed [x_dir] [z_dir]"
// Returns true on success; false on parse error (and replies ERR ...)
// ============================================================
bool parseXZStepsSpeedDir(const String& line,
                          long& xStepsOut,
                          long& zStepsOut,
                          unsigned int& xSpeedOut,
                          unsigned int& zSpeedOut,
                          int& xDirOut,
                          int& zDirOut) {
  String rest = line;
  rest.trim();

  String tokens[6];
  int tokenCount = 0;

  while (rest.length() > 0 && tokenCount < 6) {
    int sp = rest.indexOf(' ');
    if (sp < 0) {
      tokens[tokenCount++] = rest;
      break;
    }

    String tok = rest.substring(0, sp);
    tok.trim();
    if (tok.length() > 0) {
      tokens[tokenCount++] = tok;
    }
    rest = rest.substring(sp + 1);
    rest.trim();
  }

  if (tokenCount < 4) {
    reply("ERR missing_args");
    return false;
  }

  if (tokenCount > 6) {
    reply("ERR too_many_args");
    return false;
  }

  long xSteps = tokens[0].toInt();
  long zSteps = tokens[1].toInt();
  unsigned int xSpeed = (unsigned int)tokens[2].toInt();
  unsigned int zSpeed = (unsigned int)tokens[3].toInt();

  if (xSteps <= 0 || zSteps <= 0) {
    reply("ERR bad_steps");
    return false;
  }

  if (xSpeed == 0 || zSpeed == 0) {
    reply("ERR bad_speed");
    return false;
  }

  int xDir = 1;
  int zDir = 1;
  if (tokenCount >= 5) xDir = tokens[4].toInt();
  if (tokenCount >= 6) zDir = tokens[5].toInt();

  if (xSpeed < MIN_SPS) xSpeed = MIN_SPS;
  if (xSpeed > MAX_SPS) xSpeed = MAX_SPS;
  if (zSpeed < MIN_SPS) zSpeed = MIN_SPS;
  if (zSpeed > MAX_SPS) zSpeed = MAX_SPS;

  xStepsOut = xSteps;
  zStepsOut = zSteps;
  xSpeedOut = xSpeed;
  zSpeedOut = zSpeed;
  xDirOut = xDir;
  zDirOut = zDir;
  return true;
}
// ============================================================
// SETUP()
// ============================================================
// Runs once at power-up or reset.
//

void setup()
{
    // Configure control pins as OUTPUT
    pinMode(X_STEP_PIN, OUTPUT);
    pinMode(X_DIR_PIN, OUTPUT);


    pinMode(Y_STEP_PIN, OUTPUT);
    pinMode(Y_DIR_PIN, OUTPUT);

    pinMode(Z_STEP_PIN, OUTPUT);
    pinMode(Z_DIR_PIN, OUTPUT);

    pinMode(A_STEP_PIN, OUTPUT);
    pinMode(A_DIR_PIN, OUTPUT);

    pinMode(EN_PIN, OUTPUT);
    pinMode(ESTOP_PIN, INPUT_PULLUP);
    pinMode(XSTOPPER_PIN, INPUT_PULLUP);
    pinMode(YSTOPPER_PIN, INPUT_PULLUP);
    pinMode(ZSTOPPER_PIN, INPUT_PULLUP);
    pinMode(ASTOPPER_PIN, INPUT_PULLUP);

    // Start with drivers DISABLED for safety
    digitalWrite(EN_PIN, HIGH);

    // Initialize servo gripper on pin A2
    gripperServo.attach(SERVO_PIN);
    gripperServo.write(currentGripperAngle);  // Set to mid position (90°)

    // Initialize serial communication
    Serial.begin(115200);

    // Timeout for readStringUntil()
    Serial.setTimeout(100);

    // Notify host system that firmware is ready
    reply("READY");
}


// ============================================================
// LOOP()
// ============================================================
// Runs continuously.
// Waits for serial commands from Python.
//

void loop()
{

    // If E-stop button is currently pressed, latch immediately
    if (!estopLatched && isEstopActive()) {
        triggerEstop("?");
        return;
    }

    // If no serial data available → do nothing
    if (!Serial.available()){return;}
        
    // Read one full line until newline
    String line = Serial.readStringUntil('\n');
    // Remove whitespace, carriage returns, etc.
    line.trim();

    // Clear command (only allowed when button is released)
    if (line == "CLR") {
        if (isEstopActive()) {
            reply("ERR estop_still_pressed");
        } else {
            estopLatched = false;
            reply("OK estop_cleared");
        }
        return;
    }
    // ESTOP? command to query current state of E-stop button (for testing)
    if (line == "ESTOP?") {
        reply(String("ESTOP_PIN=") + digitalRead(ESTOP_PIN));
        return;
    }

    // XSTOP? command to query current state of X stopper switch (for testing)
    if (line == "XSTOP?") {
        reply(String("XSTOPPER_PIN=") + digitalRead(XSTOPPER_PIN));
        return;
    }

    // YSTOP? command to query current state of Y stopper switch (for testing)
    if (line == "YSTOP?") {
        reply(String("YSTOPPER_PIN=") + digitalRead(YSTOPPER_PIN));
        return;
    }

    // ZSTOP? command to query current state of Z stopper switch (for testing)
    if (line == "ZSTOP?") {
        reply(String("ZSTOPPER_PIN=") + digitalRead(ZSTOPPER_PIN));
        return;
    }

    // ASTOP? command to query current state of A stopper switch (for testing)
    if (line == "ASTOP?") {
        reply(String("ASTOPPER_PIN=") + digitalRead(ASTOPPER_PIN));
        return;
    }

    // ADIR? command to test A direction pin
    if (line == "ADIR?") {
        // Toggle A_DIR pin 5 times to test
        for (int i = 0; i < 5; i++) {
            digitalWrite(A_DIR_PIN, HIGH);
            delay(200);
            digitalWrite(A_DIR_PIN, LOW);
            delay(200);
        }
        reply("OK adir_toggled");
        return;
    }

    // TECH command to enable/disable technician mode
    if (line == "TECH 1") {
        technicianMode = true;
        reply("OK tech_mode_enabled");
        return;
    }
    if (line == "TECH 0") {
        technicianMode = false;
        xStopperBlockedDir = 0;  // Clear blocked directions when exiting tech mode
        yStopperBlockedDir = 0;
        zStopperBlockedDir = 0;
        aStopperBlockedDir = 0;
        reply("OK tech_mode_disabled");
        return;
    }

    // GRIP command to set gripper servo angle
    if (line.startsWith("GRIP")) {
        String rest = line.substring(4);  // after "GRIP"
        rest.trim();
        
        int angle = rest.toInt();
        
        // Validate angle range (0-180 for standard servo)
        if (angle < 0 || angle > 180) {
            reply("ERR angle_out_of_range");
            return;
        }
        
        currentGripperAngle = angle;
        gripperServo.write(angle);
        reply(String("OK grip_angle=") + angle);
        return;
    }

    // Ignore empty commands
    if (line.length() == 0){return;}
        
    // COMMAND: SYNC to test communication and get ready signal
    if (line == "SYNC")
    {
        reply("READY");
        return;
    }

    // COMMAND: ENA 1 / ENA 0 Controls driver enable state
    if (line == "ENA 1")
    {
        digitalWrite(EN_PIN, LOW);     // Enable drivers
        reply("OK enabled");
        return;
    }
    if (line == "ENA 0")
    {
        digitalWrite(EN_PIN, HIGH);    // Disable drivers
        reply("OK disabled");
        return;
    }
    
    if (estopLatched) {
    reply("ERR estop_latched");
    return;
    }

    // XZSTEP <x_steps> <z_steps> <x_speed_sps> <z_speed_sps> [x_dir] [z_dir]
    if (line.startsWith("XZSTEP")) {
      long xSteps, zSteps;
      unsigned int xSpeed, zSpeed;
      int xDir, zDir;
      String rest = line.substring(6); // after "XZSTEP"
      if (!parseXZStepsSpeedDir(rest, xSteps, zSteps, xSpeed, zSpeed, xDir, zDir)) return;
      reply("OK moving");
      bool ok = moveStepsXZCoordinated(xSteps, xDir, xSpeed, zSteps, zDir, zSpeed);
      if (ok) reply("OK done");
      return;
    }

    // --------------------------------------------------------
  // XSTEP <steps> <speed_sps> [dir]
  // Examples:
  //   XSTEP 200 800
  //   XSTEP 200 800 -1
  // --------------------------------------------------------
        // XSTEP <steps> <speed_sps> [dir]
    if (line.startsWith("XSTEP")) {
        long steps; unsigned int speed; int dir;
        // Remove command name "XSTEP"
        String rest = line.substring(5);
        if (!parseStepsSpeedDir(rest, steps, speed, dir)) return;
        reply("OK moving");
        bool ok = moveStepsAxis("X",X_STEP_PIN, X_DIR_PIN, steps, dir, speed);
        if (ok) reply("OK done");
        return;
    }
        // YSTEP <steps> <speed_sps> [dir]
    if (line.startsWith("YSTEP")) {
        long steps; unsigned int speed; int dir;
        String rest = line.substring(5); // after "YSTEP"
        if (!parseStepsSpeedDir(rest, steps, speed, dir)) return;
        reply("OK moving");
        bool ok = moveStepsAxis("Y",Y_STEP_PIN, Y_DIR_PIN, steps, dir, speed);
        if (ok) reply("OK done");
        return;
    }

    // ZSTEP <steps> <speed_sps> [dir]
    if (line.startsWith("ZSTEP")) {
        long steps; unsigned int speed; int dir;
        String rest = line.substring(5); // after "ZSTEP"
        if (!parseStepsSpeedDir(rest, steps, speed, dir)) return;
        reply("OK moving");
        bool ok = moveStepsAxis("Z",Z_STEP_PIN, Z_DIR_PIN, steps, dir, speed);
        if (ok) reply("OK done");
        return;
    }
    
    // ASTEP <steps> <speed_sps> [dir]
    if (line.startsWith("ASTEP")) {
        long steps; unsigned int speed; int dir;
        String rest = line.substring(5); // after "ASTEP"
        if (!parseStepsSpeedDir(rest, steps, speed, dir)) return;
        reply("OK moving");
        bool ok = moveStepsAxis("A",A_STEP_PIN, A_DIR_PIN, steps, dir, speed);
        if (ok) reply("OK done");
        return;
    }
       
    // --------------------------------------------------------
    // Unknown command
    // --------------------------------------------------------
    reply("ERR unknown_cmd");
}