# SCARA Robot UI - AI Build Specification (Phase 1: UI Only)

## Goal

Create a desktop UI only for the SCARA Robot project, based on the attached mockup.

This phase is UI only.
Do not connect any buttons or fields to real robot operations yet.
Use placeholder callbacks and log messages only.

## Output Location

Create the UI code in a separate folder from the firmware and current Python files.

Recommended folder structure:

```text
Scara_Robot/
├── firmware/
├── main.py
├── ui/
│   ├── app.py
│   ├── widgets.py
│   ├── styles.py
│   └── README.md
```

If a single-file version is needed first, place it in:

```text
Scara_Robot/ui/app.py
```

## Technology

Use Python.

Preferred UI framework:
1. Tkinter


Use clear object-oriented structure so the UI can later connect to:
- serial communication
- motion commands
- inverse kinematics
- homing
- estop
- status feedback

## Scope for Phase 1

Build only the visual UI layout and placeholder behavior.

### Required behavior in this phase
- All controls should be visible and aligned cleanly
- Buttons should be clickable
- Clicking any button should write a message to the log area
- No real robot movement
- No serial communication
- No backend integration
- No inverse kinematics math yet

## Window Layout

The window should follow the mockup structure:

### Main sections
1. Left panel: "Axis Direct move"
2. Right panel: "Inverse kinematics"
3. Bottom row of action buttons
4. Large log area at the bottom

## Visual Style

Target style:
- Clean engineering utility UI
- Light background
- Simple bordered panels
- Clearly grouped controls
- Easy to read labels
- Neutral styling with subtle emphasis on action buttons
- Avoid overly modern mobile-style appearance
- Keep it practical and desktop-oriented

## Main Window

### Title
Use window title:

```text
SCARA Robot Controller
```

### Minimum size
Use a reasonable desktop layout, for example:
- width: 1100-1300
- height: 650-800

The window should be resizable.

---

# Left Panel: Axis Direct move

Panel title:

```text
Axis Direct move
```

Inside this panel create rows for:

1. Y Axis
2. X Axis
3. Z Axis
4. A Axis
5. Grip

## Axis rows

For Y, X, Z, A create one row per axis.

Each row should contain:

- Axis label
- Movement label
- Input field for movement value
- Direction label
- Input field for direction value
- Speed label
- Input field for speed value
- Small action button labeled `do` 

### Labels by axis

#### Y Axis row
- Title text: `Y Axis ->`
- Movement label: `Movement (cm)`

#### X Axis row
- Title text: `X Axis ->`
- Movement label: `Movement (Deg)`

#### Z Axis row
- Title text: `Z Axis ->`
- Movement label: `Movement (Deg)`

#### A Axis row
- Title text: `A Axis ->`
- Movement label: `Movement (Deg)`

### Default placeholder text
Use placeholder text like:
- `value`
- or empty fields if the framework supports a cleaner layout

### Direction input
Keep direction as a simple text field for now.
Later it may become:
- `+`
- `-`
- `CW`
- `CCW`

### Speed input
Simple numeric text field for now.

### Row button
Each axis row should have a small button:

```text
do
```

Clicking it should append a log line like:

```text
[Y] Direct move requested (placeholder)
```

Adapt for X, Z, A.

## Grip row

Create a grip row with:

- Label: `Grip->`
- Movement label: `Movement (percent)`
- One input field
- One small `do` button

Clicking it should append:

```text
[Grip] Move requested (placeholder)
```

## Main button inside left panel

Add a larger button near the bottom of the left panel:

```text
go
```

Clicking it should append:

```text
[Direct Move] GO pressed (placeholder)
```

---

# Right Panel: Inverse kinematics

Panel title:

```text
Inverse kinematics
```

This panel is intentionally empty in phase 1 except for:
- bordered area
- title
- optional placeholder label such as:
  - `Reserved for future inverse kinematics controls`

Do not implement IK logic yet.

---

# Bottom Action Buttons

Below the two panels, create a row of buttons:

1. Exit
2. Home
3. Home Status
4. Estop
5. CLR
6. Tech

### Expected placeholder actions

#### Exit
- Close the application

#### Home
Append log:

```text
[System] Home pressed (placeholder)
```

#### Home Status
Append log:

```text
[System] Home status requested (placeholder)
```

#### Estop
Append log:

```text
[System] E-Stop pressed (placeholder)
```

#### CLR
Append log:

```text
[System] CLR pressed (placeholder)
```

#### Tech
Append log:

```text
[System] Tech pressed (placeholder)
```

---

# Log Area

At the bottom, create a large log panel.

### Requirements
- Title or label:

```text
LOG
```

- Read-only multiline text area
- Vertical scrollbar preferred
- New log messages appended at the bottom
- Timestamps optional but recommended

### Example log lines
```text
UI started
[Y] Direct move requested (placeholder)
[System] Home pressed (placeholder)
```

---

# Architecture Requirements

Use clean structure so the UI can later be connected easily.

## Suggested classes

### Main window class
Example:
```python
class ScaraMainWindow(QMainWindow):
    ...
```

### Optional helper widgets
If useful, create reusable widgets such as:
- `AxisControlRow`
- `LogPanel`
- `ActionButtonBar`

## Coding requirements
- Keep code readable
- Add comments
- Use meaningful names
- Avoid mixing layout code and future robot logic
- Keep placeholder handlers clearly separated

---

# Phase 1 Non-Goals

Do not implement:
- serial link
- protocol parsing
- motion execution
- inverse kinematics
- homing logic
- estop real function
- backend services
- firmware communication

---

# Phase 2 Preparation Notes

Design the UI so the following can be connected later:

- direct axis commands
- grouped move command
- current status display
- homing sequence
- estop latch / clear
- IK target coordinates
- live log from serial communication

---

# Deliverable

Generate Python UI code that:
- matches the described layout
- runs as a standalone app
- lives under a dedicated `ui/` folder
- uses placeholder log messages for all actions
