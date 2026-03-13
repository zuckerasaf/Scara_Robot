// ============================================================
//  SIMPLE X-AXIS STEPPER CONTROL FOR CNC SHIELD V3
//  Board: Arduino Uno
//  Driver: A4988
//  Communication: Serial (115200)
// ============================================================


// -------------------------------
// PIN DEFINITIONS
// -------------------------------
// These pin numbers match CNC Shield V3 wiring.

const int X_STEP_PIN = 2;   // STEP signal for X axis (one pulse = one step)
const int X_DIR_PIN  = 5;   // Direction signal for X axis
const int EN_PIN     = 8;   // Enable signal (shared by all drivers)


// -------------------------------
// HELPER FUNCTION: reply()
// -------------------------------
// Sends a formatted response back to Python.
// We prefix responses with "R:" so Python can detect valid replies.

void reply(const String& s)
{
  Serial.println("R:" + s);
}


// -------------------------------
// HELPER FUNCTION: stepPulse()
// -------------------------------
// Generates ONE step pulse.
// A4988 moves one microstep when STEP pin goes HIGH → LOW.

void stepPulse()
{
  digitalWrite(X_STEP_PIN, HIGH);      // Set STEP pin HIGH
  delayMicroseconds(5);                // Pulse width (minimum 1–2us required)
  digitalWrite(X_STEP_PIN, LOW);       // Set STEP pin LOW
}


// -------------------------------
// FUNCTION: moveStepsX()
// -------------------------------
// Moves X axis a given number of steps in a given direction.
//
// steps  → how many step pulses to generate
// dir    → >=0 forward, <0 reverse
//
// This function BLOCKS until movement is complete.

void moveStepsX(long steps, int dir)
{
  // Set direction first
  digitalWrite(X_DIR_PIN, (dir >= 0) ? HIGH : LOW);

  // Loop for required number of steps
  for (long i = 0; i < steps; i++)
  {
    stepPulse();                 // generate one step pulse

    delayMicroseconds(800);      // controls speed (bigger = slower)
  }
}


// -------------------------------
// SETUP()
// -------------------------------
// Runs ONCE when Arduino powers on.

void setup()
{
  // Configure motor control pins as OUTPUT
  pinMode(X_STEP_PIN, OUTPUT);
  pinMode(X_DIR_PIN, OUTPUT);
  pinMode(EN_PIN, OUTPUT);

  // Start with drivers DISABLED
  // On CNC shield:
  // LOW  = enabled
  // HIGH = disabled
  digitalWrite(EN_PIN, HIGH);

  // Start serial communication
  Serial.begin(115200);

  // Set timeout for reading serial commands
  Serial.setTimeout(100);

  // Inform host (Python) that board is ready
  reply("READY");
}


// -------------------------------
// LOOP()
// -------------------------------
// Runs repeatedly forever.
// Waits for commands from Python.

void loop()
{
  // If no data available → do nothing
  if (!Serial.available())
    return;

  // Read full line until newline
  String line = Serial.readStringUntil('\n');

  // Remove whitespace and \r characters
  line.trim();

  // If empty command → ignore
  if (line.length() == 0)
    return;


  // ---------------------------
  // COMMAND: SYNC
  // ---------------------------
  // Used by Python to verify connection.
  if (line == "SYNC")
  {
    reply("READY");
    return;
  }


  // ---------------------------
  // COMMAND: ENA 1 / ENA 0
  // ---------------------------
  // ENA 1 → enable drivers
  // ENA 0 → disable drivers

  if (line == "ENA 1")
  {
    digitalWrite(EN_PIN, LOW);      // enable driver
    reply("OK enabled");
    return;
  }

  if (line == "ENA 0")
  {
    digitalWrite(EN_PIN, HIGH);     // disable driver
    reply("OK disabled");
    return;
  }


  // ---------------------------
  // COMMAND: XSTEP <steps> [dir]
  // Example:
  //   XSTEP 200
  //   XSTEP 200 -1
  // ---------------------------

  if (line.startsWith("XSTEP"))
  {
    // Find first space
    int sp1 = line.indexOf(' ');

    if (sp1 < 0)
    {
      reply("ERR missing_steps");
      return;
    }

    // Extract everything after "XSTEP "
    String rest = line.substring(sp1 + 1);
    rest.trim();

    // Look for optional second space (direction)
    int sp2 = rest.indexOf(' ');

    String stepsStr = (sp2 < 0) ? rest : rest.substring(0, sp2);
    String dirStr   = (sp2 < 0) ? ""   : rest.substring(sp2 + 1);

    // Convert step string to integer
    long steps = stepsStr.toInt();

    if (steps <= 0)
    {
      reply("ERR bad_steps");
      return;
    }

    // Default direction = forward
    int dir = 1;

    dirStr.trim();
    if (dirStr.length() > 0)
      dir = dirStr.toInt();

    reply("OK moving");

    moveStepsX(steps, dir);

    reply("OK done");

    return;
  }


  // ---------------------------
  // UNKNOWN COMMAND
  // ---------------------------
  reply("ERR unknown_cmd");
}