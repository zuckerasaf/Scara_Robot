"""
SCARA Robot Controller - Desktop UI (Phase 1: UI Only)

This is a placeholder UI that matches the design specification.
No real robot control is implemented in this phase.
All button actions write log messages only.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import json
import os
import sys

# Add parent directory to path to import robot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_link import SerialLink
from motions import handshake, enable, wait_done 
from Robot_Command import Robot_command 

PORT = "COM3"
BAUD = 115200

def load_axis_config():
    """Load axis configuration from axis_config.json"""
    config_path = os.path.join(os.path.dirname(__file__), 'axis_config.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
        return config
    except FileNotFoundError:
        print(f"Warning: axis_config.json not found at {config_path}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error parsing axis_config.json: {e}")
        return None


class AxisControlRow(tk.Frame):
    """A single axis control row with movement, direction, speed inputs and 'do' button."""
    
    def __init__(self, parent, axis_name, movement_label, direction_options, default_direction, default_speed, log_callback, parent_window, default_steps_per_unit=1):
        super().__init__(parent, relief=tk.FLAT)
        self.axis_name = axis_name
        self.log_callback = log_callback
        self.parent_window = parent_window
        self.is_pressed = False  # Track button state
        self.default_steps_per_unit = default_steps_per_unit
        
        # Axis label
        tk.Label(self, text=f"{axis_name} Axis ->", width=10, anchor='w').grid(
            row=0, column=0, padx=5, pady=5, sticky='w'
        )
        
        # Movement
        tk.Label(self, text=movement_label, width=15, anchor='w').grid(
            row=0, column=1, padx=5, pady=5, sticky='w'
        )
        self.movement_entry = tk.Entry(self, width=10)
        self.movement_entry.grid(row=0, column=2, padx=5, pady=5)
        
        # Direction
        tk.Label(self, text="Direction", width=10, anchor='w').grid(
            row=0, column=3, padx=5, pady=5, sticky='w'
        )
        self.direction_combo = ttk.Combobox(self, width=8, values=direction_options, state='readonly')
        self.direction_combo.set(default_direction)
        self.direction_combo.grid(row=0, column=4, padx=5, pady=5)
        
        # Speed
        tk.Label(self, text="Speed", width=8, anchor='w').grid(
            row=0, column=5, padx=5, pady=5, sticky='w'
        )
        self.speed_entry = tk.Entry(self, width=10)
        self.speed_entry.insert(0, str(default_speed))  # Set default speed from config
        self.speed_entry.grid(row=0, column=6, padx=5, pady=5)
        
        # Do button (toggle button)
        self.do_button = tk.Button(
            self, text="do", width=6, 
            command=self.on_do_pressed,
            bg='#f0f0f0',
            relief=tk.RAISED
        )
        self.do_button.grid(row=0, column=7, padx=10, pady=5)
    
    def on_do_pressed(self):
        """Handle 'do' button press - toggle between pressed and normal state."""
        self.is_pressed = not self.is_pressed
        
        if self.is_pressed:
            # Button pressed in - darker color and sunken relief
            self.do_button.config(bg='#a0d0a0', relief=tk.SUNKEN)
            movement = self.movement_entry.get()
            direction = self.direction_combo.get()
            speed = self.speed_entry.get()
            
            # Apply minus sign for Down or CCW directions
            if direction in ["Down", "CCW"]:
                movement_value = f"-{movement}"
            else:
                movement_value = movement
            
            movement_value = int(float(movement_value) * self.default_steps_per_unit)  # Convert to steps using steps_per_unit
            # Build command string: "axis_name movement speed"
            cmd_string = f"{self.axis_name} {movement_value} {speed}"
            
            # Update corresponding axis command variable
            setattr(self.parent_window, f"{self.axis_name}_cmd", cmd_string)
            
            msg = f"[{self.axis_name}] Mode ACTIVE - Command: {cmd_string}"
            self.log_callback(msg)
        else:
            # Button popped out - normal appearance
            self.do_button.config(bg='#f0f0f0', relief=tk.RAISED)
            
            # Clear the axis command variable
            setattr(self.parent_window, f"{self.axis_name}_cmd", "")
            
            self.log_callback(f"[{self.axis_name}] Mode DEACTIVATED")

    def get_steps_per_unit(self, axis_name): #  """Get steps_per_unit for an axis from config"""
        if not self.axis_config or 'axes' not in self.axis_config:
            return 1.0  # Fallback: no conversion
        
        axis_data = self.axis_config['axes'].get(axis_name.upper(), {})
        # Handle both 'steps_per_unit' and 'steps_per_degree' keys
        steps = axis_data.get('steps_per_unit', axis_data.get('steps_per_degree', 1.0))
        return steps

    def get_values(self):
        """Return current input values."""
        return {
            'movement': self.movement_entry.get(),
            'direction': self.direction_combo.get(),
            'speed': self.speed_entry.get()
        }

    def reset_button(self): #"""Reset button to unpressed state."""
        if self.is_pressed:
            self.is_pressed = False
            self.do_button.config(bg='#f0f0f0', relief=tk.RAISED)
            setattr(self.parent_window, f"{self.axis_name}_cmd", "")
            self.log_callback(f"[{self.axis_name}] Mode DEACTIVATED")   

class GripControlRow(tk.Frame):
    """Gripper control row."""
    
    def __init__(self, parent, log_callback, serial_link=None):
        super().__init__(parent, relief=tk.FLAT)
        self.log_callback = log_callback
        self.link = serial_link
        
        # Grip label
        tk.Label(self, text="Grip ->", width=10, anchor='w').grid(
            row=0, column=0, padx=5, pady=5, sticky='w'
        )
        
        # Movement
        tk.Label(self, text="Movement (percent)", width=15, anchor='w').grid(
            row=0, column=1, padx=5, pady=5, sticky='w'
        )
        self.movement_entry = tk.Entry(self, width=10)
        self.movement_entry.grid(row=0, column=2, padx=5, pady=5)
        
        # Spacer to align with axis rows
        tk.Label(self, text="", width=10).grid(row=0, column=3, padx=5)
        tk.Label(self, text="", width=10).grid(row=0, column=4, padx=5)
        tk.Label(self, text="", width=8).grid(row=0, column=5, padx=5)
        tk.Label(self, text="", width=10).grid(row=0, column=6, padx=5)
        
        # Do button
        self.do_button = tk.Button(
            self, text="do", width=6,
            command=self.on_do_pressed,
            bg='#f0f0f0'
        )
        self.do_button.grid(row=0, column=7, padx=10, pady=5)
    
    def on_do_pressed(self):
        """Handle 'do' button press."""
        movement = self.movement_entry.get()
        
        if not self.link:
            self.log_callback("[Grip] ERROR: Not connected to robot")
            return
        
        try:
            angle = int(movement)
            if angle < 0 or angle > 180:
                self.log_callback("[Grip] ERROR: Angle must be 0-180")
                return
            
            cmd = f"grip {angle}"
            self.log_callback(f"[Grip] Command (placeholder): {cmd}")
            
            # TODO: Send command using Robot_command when connection is implemented
            # response = Robot_command(cmd, self.link)
            # self.log_callback(f"[Grip] {response}")
            
        except ValueError:
            self.log_callback("[Grip] ERROR: Invalid angle value")
    
    def get_value(self):
        """Return current grip value."""
        return self.movement_entry.get()


class LogPanel(tk.Frame):
    """Log panel with scrollable text area."""
    
    def __init__(self, parent):
        super().__init__(parent, relief=tk.GROOVE, borderwidth=2)
        
        # Title
        tk.Label(self, text="LOG", font=('Arial', 10, 'bold'), anchor='w').pack(
            side=tk.TOP, fill=tk.X, padx=5, pady=5
        )
        
        # Scrolled text widget
        self.text_area = scrolledtext.ScrolledText(
            self, 
            wrap=tk.WORD, 
            width=100, 
            height=12,
            font=('Courier', 9),
            bg='#ffffff',
            state=tk.DISABLED
        )
        self.text_area.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
    
    def append_log(self, message):
        """Append a message to the log with timestamp."""
        now = datetime.now()
        timestamp = now.strftime("%H:%M:%S") + f".{now.microsecond // 1000:03d}"
        log_line = f"[{timestamp}] {message}\n"
        
        self.text_area.config(state=tk.NORMAL)
        self.text_area.insert(tk.END, log_line)
        self.text_area.see(tk.END)  # Auto-scroll to bottom
        self.text_area.config(state=tk.DISABLED)


class ScaraMainWindow:
    """Main window for SCARA Robot Controller."""
    
    def __init__(self, root, serial_link=None):
        self.root = root
        self.root.title("SCARA Robot Controller")
        self.root.geometry("1200x750")
        self.root.minsize(1200, 750)
        
        # Serial link
        self.link = serial_link
        
        # Axis command strings (updated when 'do' buttons are pressed)
        self.X_cmd = ""
        self.Y_cmd = ""
        self.Z_cmd = ""
        self.A_cmd = ""
        
        # Y axis movement limiters (how much movement remaining in each direction)
        self.Y_upper_limit = 0  # Remaining movement up (in steps)
        self.Y_lower_limit = 0  # Remaining movement down (in steps)
        
        # Axis stopper status (True = pressed, False = not pressed)
        self.Y_stopper_status = False
        self.X_stopper_status = False
        self.Z_stopper_status = False
        self.A_stopper_status = False
        
        # Axis homing status (True = homed, False = not homed)
        self.Y_homing_status = False
        self.X_homing_status = False
        self.Z_homing_status = False
        self.A_homing_status = False
        
        # Load axis configuration
        self.axis_config = load_axis_config()
        
        # Configure root grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)
        main_container.columnconfigure(1, weight=1)
        main_container.rowconfigure(0, weight=3)
        main_container.rowconfigure(1, weight=0)
        main_container.rowconfigure(2, weight=0)
        main_container.rowconfigure(3, weight=2)
        
        # Create panels
        self.create_left_panel(main_container)
        self.create_right_panel(main_container)
        self.create_status_panel(main_container)
        self.create_action_buttons(main_container)
        self.create_log_panel(main_container)
        
        # Initial log message
        self.log("UI started")
        if self.axis_config:
            self.log("Axis configuration loaded from axis_config.json")
        else:
            self.log("Warning: Using default values (axis_config.json not loaded)")
        
        # Log connection status
        if self.link:
            self.log("Connected to SCARA robot")
            # Query initial stopper status
            self.root.after(500, self.update_all_stopper_status)  # Delay to let UI settle
        else:
            self.log("WARNING: Not connected to robot - running in offline mode")
    
    def get_axis_defaults(self, axis_name):
        """Get default speed and direction for an axis from config"""
        if not self.axis_config or 'axes' not in self.axis_config:
            return 500, 1  # Fallback defaults
        
        axis_data = self.axis_config['axes'].get(axis_name.upper(), {})
        default_speed = axis_data.get('default_speed', 500)
        default_direction = axis_data.get('default_direction', 1)
        default_steps_per_unit = axis_data.get('steps_per_unit', 1)
        min_limit = axis_data.get('min_limit', 0)
        max_limit = axis_data.get('max_limit', 1000)
        
        return default_speed, default_direction, default_steps_per_unit, min_limit, max_limit
    
    def direction_to_text(self, direction_value, direction_options):
        """Convert direction value (1/-1) to UI text"""
        # 1 = first option (Up, CW)
        # -1 = second option (Down, CCW)
        if direction_value == 1:
            return direction_options[0]
        else:
            return direction_options[1]
    
    def create_left_panel(self, parent):
        """Create left panel: Axis Direct move."""
        panel = tk.LabelFrame(
            parent, 
            text="Axis Direct move", 
            font=('Arial', 11, 'bold'),
            relief=tk.GROOVE,
            borderwidth=2,
            bg='#ffffff',
            padx=10,
            pady=10
        )
        panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=(0, 5))
        
        # Get defaults from config
        y_speed, y_dir, y_steps_per_unit , y_min_limit, y_max_limit = self.get_axis_defaults('Y')
        x_speed, x_dir, x_steps_per_unit , x_min_limit, x_max_limit = self.get_axis_defaults('X')
        z_speed, z_dir, z_steps_per_unit , z_min_limit, z_max_limit = self.get_axis_defaults('Z')
        a_speed, a_dir, a_steps_per_unit , a_min_limit, a_max_limit = self.get_axis_defaults('A')
        
        # Create axis control rows
        # Y axis: Up/Down direction
        y_direction_opts = ["Up", "Down"]
        self.y_axis = AxisControlRow(
            panel, "Y", "Movement (cm)", 
            y_direction_opts, 
            self.direction_to_text(y_dir, y_direction_opts),
            y_speed,
            self.log,
            self,
            y_steps_per_unit
        )
        self.y_axis.pack(fill=tk.X, pady=5)
        
        # X axis: CW/CCW direction
        x_direction_opts = ["CW", "CCW"]
        self.x_axis = AxisControlRow(
            panel, "X", "Movement (Deg)", 
            x_direction_opts,
            self.direction_to_text(x_dir, x_direction_opts),
            x_speed,
            self.log,
            self,
            x_steps_per_unit
        )
        self.x_axis.pack(fill=tk.X, pady=5)
        
        # Z axis: CW/CCW direction
        z_direction_opts = ["CW", "CCW"]
        self.z_axis = AxisControlRow(
            panel, "Z", "Movement (Deg)", 
            z_direction_opts,
            self.direction_to_text(z_dir, z_direction_opts),
            z_speed,
            self.log,
            self,
            z_steps_per_unit     
        )
        self.z_axis.pack(fill=tk.X, pady=5)
        
        # A axis: CW/CCW direction
        a_direction_opts = ["CW", "CCW"]
        self.a_axis = AxisControlRow(
            panel, "A", "Movement (Deg)", 
            a_direction_opts,
            self.direction_to_text(a_dir, a_direction_opts),
            a_speed,
            self.log,
            self,
            a_steps_per_unit
        )
        self.a_axis.pack(fill=tk.X, pady=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Grip control
        self.grip = GripControlRow(panel, self.log, self.link)
        self.grip.pack(fill=tk.X, pady=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=15)
        
        # GO button
        go_button = tk.Button(
            panel, 
            text="go", 
            font=('Arial', 12, 'bold'),
            width=15,
            height=2,
            command=self.on_go_pressed,
            bg='#e0e0e0',
            activebackground='#d0d0d0'
        )
        go_button.pack(pady=10)
    
    def create_right_panel(self, parent):
        """Create right panel: Inverse kinematics (empty for Phase 1)."""
        panel = tk.LabelFrame(
            parent,
            text="Inverse kinematics",
            font=('Arial', 11, 'bold'),
            relief=tk.GROOVE,
            borderwidth=2,
            bg='#ffffff',
            padx=10,
            pady=10
        )
        panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0), pady=(0, 5))
        
        # Placeholder label
        placeholder = tk.Label(
            panel,
            text="Reserved for future inverse kinematics controls",
            font=('Arial', 10, 'italic'),
            fg='#888888',
            bg='#ffffff'
        )
        placeholder.pack(expand=True)
    
    def create_status_panel(self, parent):
        """Create status panel showing stopper and homing status."""
        status_frame = tk.Frame(parent, relief=tk.GROOVE, borderwidth=2, bg='#ffffff')
        status_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=0, pady=(5, 5))
        
        # Configure grid for 4 columns (one per axis)
        for i in range(4):
            status_frame.columnconfigure(i, weight=1, uniform="axis")
        
        # Axis names
        axes = ['Y', 'X', 'Z', 'A']
        
        # Stopper status indicators
        self.stopper_indicators = {}
        self.homing_indicators = {}
        self.remain_entries = {}  # Store Entry widgets for remain values (upper/lower for each axis)
        
        for col, axis in enumerate(axes):
            # Axis label
            tk.Label(status_frame, text=f"{axis} Axis Status", font=('Arial', 9, 'bold'), bg='#ffffff').grid(
                row=0, column=col, padx=5, pady=(5, 2)
            )
            
            # Stopper status
            stopper_frame = tk.Frame(status_frame, bg='#ffffff')
            stopper_frame.grid(row=1, column=col, padx=5, pady=2)
            tk.Label(stopper_frame, text="Stopper:", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            self.stopper_indicators[axis] = tk.Canvas(stopper_frame, width=20, height=20, bg='#ffffff', highlightthickness=1, highlightbackground='#888888')
            self.stopper_indicators[axis].pack(side=tk.LEFT, padx=5)
            self.stopper_indicators[axis].create_oval(5, 5, 15, 15, fill='#cccccc', outline='#888888', tags='indicator')
            
            # Homing status
            homing_frame = tk.Frame(status_frame, bg='#ffffff')
            homing_frame.grid(row=2, column=col, padx=5, pady=2)
            tk.Label(homing_frame, text="After Homing:", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            self.homing_indicators[axis] = tk.Canvas(homing_frame, width=20, height=20, bg='#ffffff', highlightthickness=1, highlightbackground='#888888')
            self.homing_indicators[axis].pack(side=tk.LEFT, padx=5)
            self.homing_indicators[axis].create_oval(5, 5, 15, 15, fill='#cccccc', outline='#888888', tags='indicator')
            
            # Remain values (placeholder)
            remain_frame = tk.Frame(status_frame, bg='#ffffff')
            remain_frame.grid(row=3, column=col, padx=5, pady=(2, 5))
            
            if axis == 'Y':
                dir_text = "Remain Up/Down"
            else:
                dir_text = "Remain CW/CCW"
            
            tk.Label(remain_frame, text=dir_text, font=('Arial', 7), bg='#ffffff').pack()
            remain_values = tk.Frame(remain_frame, bg='#ffffff')
            remain_values.pack()
            
            # Create Entry widgets and store references
            tk.Label(remain_values, text="↑" if axis == 'Y' else "↻", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            upper_entry = tk.Entry(remain_values, width=6, font=('Arial', 7))
            upper_entry.pack(side=tk.LEFT, padx=2)
            upper_entry.config(state='readonly')
            
            tk.Label(remain_values, text="↓" if axis == 'Y' else "↺", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            lower_entry = tk.Entry(remain_values, width=6, font=('Arial', 7))
            lower_entry.pack(side=tk.LEFT, padx=2)
            lower_entry.config(state='readonly')
            
            # Store Entry widgets for later updates
            self.remain_entries[axis] = {'upper': upper_entry, 'lower': lower_entry}
            
            # Set initial values for Y axis
            if axis == 'Y':
                upper_entry.config(state='normal')
                upper_entry.delete(0, tk.END)
                upper_entry.insert(0, str(self.Y_upper_limit))
                upper_entry.config(state='readonly')
                
                lower_entry.config(state='normal')
                lower_entry.delete(0, tk.END)
                lower_entry.insert(0, str(self.Y_lower_limit))
                lower_entry.config(state='readonly')
    
    def create_action_buttons(self, parent):
        """Create bottom action button row."""
        button_frame = tk.Frame(parent, bg='#f5f5f5')
        button_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(5, 5))
        
        # Button configuration
        button_config = {
            'width': 12,
            'height': 2,
            'font': ('Arial', 10)
        }
        
        # Exit button (red)
        btn_exit = tk.Button(
            button_frame, 
            text="Exit", 
            command=self.on_exit,
            bg='#ffcccc',
            activebackground='#ffaaaa',
            **button_config
        )
        btn_exit.pack(side=tk.LEFT, padx=5)
        
        # Home button (green)
        btn_home = tk.Button(
            button_frame,
            text="Home",
            command=self.on_home,
            bg='#ccffcc',
            activebackground='#aaffaa',
            **button_config
        )
        btn_home.pack(side=tk.LEFT, padx=5)
        
        # Home Status button
        btn_home_status = tk.Button(
            button_frame,
            text="Home Status",
            command=self.on_home_status,
            bg='#e0e0e0',
            **button_config
        )
        btn_home_status.pack(side=tk.LEFT, padx=5)
        
        # Estop button (red)
        btn_estop = tk.Button(
            button_frame,
            text="Estop",
            command=self.on_estop,
            bg='#ffcccc',
            activebackground='#ffaaaa',
            **button_config
        )
        btn_estop.pack(side=tk.LEFT, padx=5)
        
        # CLR button (yellow)
        btn_clr = tk.Button(
            button_frame,
            text="CLR",
            command=self.on_clr,
            bg='#ffffcc',
            activebackground='#ffffaa',
            **button_config
        )
        btn_clr.pack(side=tk.LEFT, padx=5)
        
        # Tech button
        btn_tech = tk.Button(
            button_frame,
            text="Tech",
            command=self.on_tech,
            bg='#e0e0e0',
            **button_config
        )
        btn_tech.pack(side=tk.LEFT, padx=5)
        
        # Sync button (blue)
        btn_sync = tk.Button(
            button_frame,
            text="Sync",
            command=self.on_sync,
            bg='#ccddff',
            activebackground='#aaccff',
            **button_config
        )
        btn_sync.pack(side=tk.LEFT, padx=5)
    
    def create_log_panel(self, parent):
        """Create log panel at the bottom."""
        self.log_panel = LogPanel(parent)
        self.log_panel.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
    
    def log(self, message):
        """Add a message to the log."""
        self.log_panel.append_log(message)
    
    def update_stopper_indicator(self, axis, is_pressed):
        """Update stopper indicator for an axis.
        
        Args:
            axis: Axis name ('X', 'Y', 'Z', or 'A')
            is_pressed: True if stopper is pressed, False otherwise
        """
        if axis in self.stopper_indicators:
            color = '#ff4444' if is_pressed else '#44ff44'  # Red if pressed, green if not
            self.stopper_indicators[axis].itemconfig('indicator', fill=color)
            
            # Update boolean status variable
            setattr(self, f"{axis}_stopper_status", is_pressed)
            
            self.root.update()
    
    def update_homing_indicator(self, axis, is_homed):
        """Update homing indicator for an axis.
        
        Args:
            axis: Axis name ('X', 'Y', 'Z', or 'A')
            is_homed: True if axis is homed, False otherwise
        """
        if axis in self.homing_indicators:
            color = '#44ff44' if is_homed else '#cccccc'  # Green if homed, gray if not
            self.homing_indicators[axis].itemconfig('indicator', fill=color)
            
            # Update boolean status variable
            setattr(self, f"{axis}_homing_status", is_homed)
            
            self.root.update()
    
    def update_Y_remain_values(self, axis, cmd):
        homestate = getattr(self, f"{axis}_homing_status", 0)
        if homestate:
            self.update_limiters_value(axis, cmd)
            """Update Y axis remain values display with current limits."""
            if 'Y' in self.remain_entries:
                # Update upper limit (up direction)
                upper_entry = self.remain_entries['Y']['upper']
                upper_entry.config(state='normal')
                upper_entry.delete(0, tk.END)
                upper_entry.insert(0, str(self.Y_upper_limit))
                upper_entry.config(state='readonly')
                
                # Update lower limit (down direction)
                lower_entry = self.remain_entries['Y']['lower']
                lower_entry.config(state='normal')
                lower_entry.delete(0, tk.END)
                lower_entry.insert(0, str(self.Y_lower_limit))
                lower_entry.config(state='readonly')
                
                self.root.update()
    def update_limiters_value(self, axis, cmd):
        if axis == 'Y': 
            max_value = self.y_max_limit
            self.Y_upper_limit = max_value-abs(int(cmd.split(" ")[1]))
            self.Y_lower_limit = abs(int(cmd.split(" ")[1]))

    def query_stopper_status(self, axis):
        """Query stopper status from robot for a specific axis.
        
        Args:
            axis: Axis name ('X', 'Y', 'Z', or 'A')
        
        Returns:
            True if stopper is pressed, False otherwise
        """
        if not self.link:
            return False
        
        try:
            cmd = f"{axis.upper()}STOP?"
            response = Robot_command(cmd, self.link, self.log)
            # Response format: "R:XSTOPPER_PIN=0" or "R:XSTOPPER_PIN=1"
            if "=1" in response:
                return True
            return False
        except Exception as e:
            self.log(f"[Status] Error querying {axis} stopper: {e}")
            self.root.update()
            return False
    
    def update_all_stopper_status(self):
        """Query and update stopper status for all axes."""
        for axis in ['Y', 'X', 'Z', 'A']:
            is_pressed = self.query_stopper_status(axis)
            self.update_stopper_indicator(axis, is_pressed)
    
    # ============================================================
    # Button Callbacks (Placeholders for Phase 1)
    # ============================================================
    
    def on_go_pressed(self, timeout_s=10.0):
        """Handle GO button press - execute all active axis commands."""
        if not self.link:
            self.log("[GO] ERROR: Not connected to robot")
            self.root.update()  # Force UI update
            return
        
        # List of axis commands in order
        axis_commands = [
            ('X', self.X_cmd),
            ('Y', self.Y_cmd),
            ('Z', self.Z_cmd),
            ('A', self.A_cmd)
        ]
        
        # Track if any commands were executed
        executed_count = 0
        
        # Execute each non-empty command in order
        for axis_name, cmd in axis_commands:
            if cmd:  # Only execute if command is not empty
                try:
                    import time
                    start_time = time.time()

                    self.log(f"[GO] Executing on_go_pressed on {axis_name}: {cmd}")
                    self.root.update()  # Force UI update
                    response = Robot_command(cmd, self.link, self.log)
                    
                    calc_time = abs(int(cmd.split(" ")[1])/int(cmd.split(" ")[2])) + 1
                    timeout = calc_time
                    movement_done = False
                    done_response = ""
                    
                    self.log(f"[GO] start the waiting phase  {axis_name}: {cmd}")
                    self.root.update()  # Force UI update
                    # Poll for completion within timeout
                    while (time.time() - start_time) < timeout:
                        try:
                            # Read response from robot (non-blocking)
                            done_response = self.link.ser.readline().decode(errors="ignore").strip()
                            
                            if done_response == "R:OK done":
                                movement_done = True
                                self.log(f"[GO] {axis_name} completed successfully in {int(time.time() - start_time)}s (calc time: {calc_time}s)")
                                # Query actual stopper status after movement
                                is_pressed = self.query_stopper_status(axis_name)
                                self.update_stopper_indicator(axis_name, is_pressed)
                                self.update_Y_remain_values(axis_name, cmd)
                                self.root.update()  # Force UI update
                                break
                            elif "STOPPER_HIT" in done_response or "R:ERR" in done_response:
                                self.log(f"[GO] {axis_name} error: {done_response}")
                                # Update stopper indicator if stopper was hit
                                if "STOPPER_HIT" in done_response:
                                    self.update_stopper_indicator(axis_name, True)
                                self.root.update()  # Force UI update
                                break
                            elif done_response and done_response != "":
                                # Log any other response received
                                self.log(f"[GO] {axis_name} received: {done_response}")
                                self.root.update()  # Force UI update
                                
                        except Exception as e:
                            self.log(f"[GO] Read error: {e}")
                            self.root.update()  # Force UI update
                            break
                        
                        # Small delay to avoid busy-waiting
                        time.sleep(0.1)

                    # Check result and query stopper status
                    if not movement_done:
                        self.log(f"[GO] {axis_name} TIMEOUT - no completion after {timeout}s")
                        # Query actual stopper status after timeout
                        is_pressed = self.query_stopper_status(axis_name)
                        self.update_stopper_indicator(axis_name, is_pressed)
                        self.root.update()  # Force UI update


                    executed_count += 1
                except Exception as e:
                    self.log(f"[GO] ERROR on {axis_name}: {e}")
                    self.root.update()  # Force UI update
                    # Optionally, you can decide whether to continue or stop here
                    # To stop on error, add: return
        
        if executed_count == 0:
            self.log("[GO] No active axis commands to execute")
            self.root.update()  # Force UI update
        else:
            self.log(f"[GO] Completed {executed_count} axis commands in {time.time() - start_time:.2f}s")
            self.root.update()  # Force UI update

        # Reset all axis buttons to unpressed state
        self.x_axis.reset_button()
        self.y_axis.reset_button()
        self.z_axis.reset_button()
        self.a_axis.reset_button()
            # In the ScaraMainWindow class, add:
    def cleanup_and_exit(self):
        """Cleanup and exit the application."""
        self.log("[System] Shutting down...")
        self.root.update()  # Force UI update
        if self.link:
            enable(self.link, False)
            self.link.close()
        self.root.destroy()


    def on_exit(self):
        """Handle Exit button press."""
        self.log("[System] Exit pressed - closing application")
        self.root.update()  # Force UI update
        self.cleanup_and_exit()
    

    def updete_axis_command(self, axis_name, cmd):
        """Update the command string for an axis."""
        if axis_name == "Y":
            self.Y_cmd = cmd
            return True
        elif axis_name == "X":
            self.X_cmd = cmd    
            return True
        elif axis_name == "Z":
            self.Z_cmd = cmd
            return True
        elif axis_name == "A":
            self.A_cmd = cmd
            return True
        else:
            self.log(f"[Update Command] ERROR: Invalid axis name {axis_name}")
            self.root.update()  # Force UI update
            return False

    def home_axis(self, Axis_name, cmd, cmd_back):
        status = "Failed homing"
        self.Y_cmd = ""
        self.X_cmd = ""
        self.Z_cmd = ""
        self.A_cmd = ""

        axiesUpdate = self.updete_axis_command(Axis_name, cmd)
        if not axiesUpdate: 
            self.log(f"[Home] ERROR: Invalid axis name {Axis_name} for homing")
            self.root.update()  # Force UI update
            return Axis_name + " Failed homing - invalid axis name"   
          
        self.on_go_pressed() 
        
        # Check stopper status using boolean variable
        stopper_status = getattr(self, f"{Axis_name}_stopper_status")
        
        if stopper_status:  # True means stopper is pressed (hit)
            status = " Homed"
            self.log(f"[Home] {Axis_name} HOMED successfully")
            self.update_homing_indicator(Axis_name, True)  # Update homing indicator
            self.root.update()  # Force UI update
            axiesUpdate = self.updete_axis_command(Axis_name, cmd_back)
            if axiesUpdate:
                self.on_go_pressed()    
            else:
                self.log(f"[Home] ERROR: Invalid axis name {Axis_name} for homing back command")
                self.root.update()  # Force UI update
                return Axis_name + " Failed homing - invalid axis name for back command"
        else :
            self.log(f"[Home] {Axis_name} FAILED to home - no stopper hit")
            self.update_homing_indicator(Axis_name, False)  # Update homing indicator
            self.root.update()  # Force UI update
            status = " Failed homing"
        return Axis_name + status 

    def on_home(self):
        import time
        """Handle Home button press - execute homing sequence for all axes."""
        homed_axes = []
        timeOutHome = 10
        import time
    #"""Handle Home button press - execute homing sequence for all axes."""
        if not self.link:
            self.log("[Home] ERROR: Not connected to robot")
            self.root.update()  # Force UI update
            return
        self.log("[Home] Starting homing sequence for all axes")
        self.root.update()  # Force UI update
        Y = "Y 20000 1000"
        Y2 = "Y -200 1000"
        self.home_axis("Y", Y, Y2)

        #homed_axes.append( "Y homeing = " + status + ", ")


        

    
    def on_home_status(self):
        """Handle Home Status button press - query and display all stopper and homing status."""
        if not self.link:
            self.log("[Status] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[Status] Querying stopper status for all axes...")
        self.root.update()
        
        # Query and update all stopper statuses
        self.update_all_stopper_status()
        
        self.log("[Status] Stopper status updated")
        self.root.update()
    
    def on_estop(self):
        """Handle Estop button press."""
        self.log("[System] E-Stop pressed (placeholder)")
        self.root.update()  # Force UI update
    
    def on_clr(self):
        """Handle CLR button press."""
        self.log("[System] CLR pressed (placeholder)")
        self.root.update()  # Force UI update
    
    def on_tech(self):
        """Handle Tech button press."""
        self.log("[System] Tech pressed (placeholder)")
        self.root.update()  # Force UI update
    
    def on_sync(self):
        """Handle Sync button press - perform handshake with robot."""
        if not self.link:
            self.log("[Sync] ERROR: Not connected to robot")
            self.root.update()  # Force UI update
            return
        
        self.log("[Sync] Sending handshake...")
        self.root.update()  # Force UI update
        try:
            ans= Robot_command("sync",self.link)
            self.log(f"[Sync] SUCCESS: Robot responded READY = {ans}")
            self.root.update()  # Force UI update
        except Exception as e:
            self.log(f"[Sync] ERROR: {e}")
            self.root.update()  # Force UI update


def main():
    """Main entry point for the application."""
    # Try to connect to the robot
    link = None
    try:
        link = SerialLink(PORT, BAUD)
        link.open()  # Open the serial connection
        if handshake(link):
            print("Handshake successful - robot connected")
            enable(link, True)  # Enable motors
            print("Motors enabled")
        else:
            print("Handshake failed - continuing in offline mode")
            link.close()
            link = None
    except Exception as e:
        print(f"Failed to connect to robot: {e}")
        print("Starting UI in offline mode")
        if link:
            link.close()
        link = None
    
    # Start the UI
    root = tk.Tk()
    app = ScaraMainWindow(root, serial_link=link)
    
    # Cleanup on exit
    def on_closing():
        app.cleanup_and_exit()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
