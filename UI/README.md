# SCARA Robot UI - Phase 1

This is the desktop user interface for the SCARA Robot Controller, built with Python Tkinter.

## Current Status: Phase 1 (UI Only)

This phase implements only the visual interface and placeholder functionality.
**No real robot control is implemented yet.**

All buttons write log messages only.

## Requirements

- Python 3.7+
- tkinter (usually included with Python)

## Running the UI

From the project root directory:

```bash
cd ui
python app.py
```

Or from anywhere:

```bash
python c:\projectPython\Scara_Robot\ui\app.py
```

## Features (Phase 1)

### Left Panel: Axis Direct Move
- **Y Axis**: Movement (cm), Direction, Speed controls
- **X Axis**: Movement (Deg), Direction, Speed controls
- **Z Axis**: Movement (Deg), Direction, Speed controls
- **A Axis**: Movement (Deg), Direction, Speed controls
- **Grip**: Movement (percent) control
- **GO button**: Main execute button (placeholder)

Each axis row has a "do" button for individual axis commands.

### Right Panel: Inverse Kinematics
- Reserved for future IK controls (empty in Phase 1)

### Bottom Action Buttons
- **Exit**: Close the application
- **Home**: Home all axes (placeholder)
- **Home Status**: Query homing status (placeholder)
- **Estop**: Emergency stop (placeholder)
- **CLR**: Clear emergency stop (placeholder)
- **Tech**: Technician mode toggle (placeholder)

### Log Panel
- Displays all actions with timestamps
- Auto-scrolls to latest message
- Read-only view

## Code Structure

```
ui/
├── app.py          # Main application file
└── README.md       # This file
```

### Main Classes

- **`ScaraMainWindow`**: Main application window
- **`AxisControlRow`**: Reusable widget for each axis control row
- **`GripControlRow`**: Gripper control widget
- **`LogPanel`**: Scrollable log display

## Phase 2 Plans (Future)

The UI is designed to easily integrate:
- Serial communication with Arduino firmware
- Real motion commands (XSTEP, YSTEP, ZSTEP, ASTEP, GRIP)
- Inverse kinematics calculations
- Homing sequence execution
- E-stop latch/clear functionality
- Live status updates from robot
- Real-time position feedback

## Design Notes

- Clean object-oriented structure
- Placeholder callbacks ready for backend integration
- Follows engineering utility UI style
- Desktop-oriented layout (resizable)
- Neutral color scheme with subtle emphasis on critical buttons

## Customization

To adjust window size, modify in `app.py`:
```python
self.root.geometry("1200x750")  # width x height
self.root.minsize(1100, 650)    # minimum size
```

## Testing

All buttons and controls should be functional:
1. Enter values in any axis row
2. Click "do" button
3. Observe log message with entered values
4. Test all bottom action buttons
5. Verify log auto-scrolling

## Next Steps

Before Phase 2 integration:
1. Test UI layout on target system
2. Verify all controls are accessible
3. Adjust styling if needed
4. Prepare backend integration points
