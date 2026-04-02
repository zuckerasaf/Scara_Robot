"""
SCARA Robot Controller - UI Layer

This module contains all Tkinter UI components and visual elements.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import math


class AxisControlRow(tk.Frame):
    """A single axis control row with movement, direction, speed inputs and 'do' button."""
    
    def __init__(self, parent, axis_name, movement_label, direction_options, default_direction, 
                 default_speed, log_callback, robot_controller, default_steps_per_unit=1):
        super().__init__(parent, relief=tk.FLAT)
        self.axis_name = axis_name
        self.log_callback = log_callback
        self.robot_controller = robot_controller
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
        self.speed_entry.insert(0, str(default_speed))
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
            
            movement_value = int(float(movement_value) * self.default_steps_per_unit)
            cmd_string = f"{self.axis_name} {movement_value} {speed}"
            
            # Update controller's axis command
            self.robot_controller.update_axis_command(self.axis_name, cmd_string)
            
            msg = f"[{self.axis_name}] Mode ACTIVE - Command: {cmd_string}"
            self.log_callback(msg)
        else:
            # Button popped out - normal appearance
            self.do_button.config(bg='#f0f0f0', relief=tk.RAISED)
            
            # Clear the axis command
            self.robot_controller.update_axis_command(self.axis_name, "")
            
            self.log_callback(f"[{self.axis_name}] Mode DEACTIVATED")
    
    def reset_button(self):
        """Reset button to unpressed state and zero axis command."""
        if self.is_pressed:
            self.is_pressed = False
            self.do_button.config(bg='#f0f0f0', relief=tk.RAISED)
            # Zero out axis command to prevent unwanted data
            self.robot_controller.update_axis_command(self.axis_name, "")
            self.log_callback(f"[{self.axis_name}] Mode DEACTIVATED - Command cleared")



class GripControlRow(tk.Frame):
    """Gripper control row."""
    
    def __init__(self, parent, log_callback, robot_controller):
        super().__init__(parent, relief=tk.FLAT)
        self.log_callback = log_callback
        self.robot_controller = robot_controller
        
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
        
        # Helper label showing open/close values
        tk.Label(self, text="91=open \\ 179=close", width=20, anchor='w', 
                 font=('Arial', 8, 'italic'), fg='#666666').grid(row=0, column=3, padx=5, pady=5, sticky='w')
        
        # Spacer to align with axis rows
        tk.Label(self, text="", width=10).grid(row=0, column=4, padx=5)
        tk.Label(self, text="", width=8).grid(row=0, column=5, padx=5)
        tk.Label(self, text="", width=10).grid(row=0, column=6, padx=5)
        
        # Do button
        self.do_button = tk.Button(
            self, text="Go_Grip", width=6,
            command=self.on_Go_Grip_pressed,
            bg='#f0f0f0'
        )
        self.do_button.grid(row=0, column=7, padx=10, pady=5)
    
    def on_Go_Grip_pressed(self):
        """Handle 'Go_Grip' button press."""
        movement = self.movement_entry.get()
        
        if not self.robot_controller.link:
            self.log_callback("[Grip] ERROR: Not connected to robot")
            return
        
        try:
            angle = int(movement)
            # Send grip command to robot (validation done in controller)
            self.robot_controller.grip(angle)
            
        except ValueError:
            self.log_callback("[Grip] ERROR: Invalid angle value")


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
    """Main window for SCARA Robot Controller - UI Layer Only"""
    
    def __init__(self, root, robot_controller):
        """
        Initialize main window.
        
        Args:
            root: Tkinter root window
            robot_controller: RobotController instance for business logic
        """
        self.root = root
        self.robot_controller = robot_controller
        
        # Configure window
        self.root.title("SCARA Robot Controller")
        self.root.geometry("1400x1100")
        self.root.minsize(1400, 1100)
        
        # Tech mode state
        self.tech_mode_enabled = False
        
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
        
        # Initial log messages
        self.log("UI started")
        if self.robot_controller.axis_config:
            self.log("Axis configuration loaded from axis_config.json")
        else:
            self.log("Warning: Using default values (axis_config.json not loaded)")
        
        # Log connection status
        if self.robot_controller.link:
            self.log("Connected to SCARA robot")
            # Query initial stopper status
            self.root.after(500, self.update_all_stopper_status)
        else:
            self.log("WARNING: Not connected to robot - running in offline mode")
    
    def log(self, message):
        """Add a message to the log."""
        self.log_panel.append_log(message)
    
    def direction_to_text(self, direction_value, direction_options):
        """Convert direction value (1/-1) to UI text"""
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
        y_speed, y_dir, y_steps_per_unit, y_min_limit, y_max_limit = self.robot_controller.get_axis_defaults('Y')
        x_speed, x_dir, x_steps_per_unit, x_min_limit, x_max_limit = self.robot_controller.get_axis_defaults('X')
        z_speed, z_dir, z_steps_per_unit, z_min_limit, z_max_limit = self.robot_controller.get_axis_defaults('Z')
        a_speed, a_dir, a_steps_per_unit, a_min_limit, a_max_limit = self.robot_controller.get_axis_defaults('A')
        
        # Create axis control rows
        y_direction_opts = ["Up", "Down"]
        self.y_axis = AxisControlRow(
            panel, "Y", "Movement (cm)", 
            y_direction_opts, 
            self.direction_to_text(y_dir, y_direction_opts),
            y_speed,
            self.log,
            self.robot_controller,
            y_steps_per_unit
        )
        self.y_axis.pack(fill=tk.X, pady=5)
        
        x_direction_opts = ["CW", "CCW"]
        self.x_axis = AxisControlRow(
            panel, "X", "Movement (Deg)", 
            x_direction_opts,
            self.direction_to_text(x_dir, x_direction_opts),
            x_speed,
            self.log,
            self.robot_controller,
            x_steps_per_unit
        )
        self.x_axis.pack(fill=tk.X, pady=5)
        
        z_direction_opts = ["CW", "CCW"]
        self.z_axis = AxisControlRow(
            panel, "Z", "Movement (Deg)", 
            z_direction_opts,
            self.direction_to_text(z_dir, z_direction_opts),
            z_speed,
            self.log,
            self.robot_controller,
            z_steps_per_unit     
        )
        self.z_axis.pack(fill=tk.X, pady=5)
        
        a_direction_opts = ["CW", "CCW"]
        self.a_axis = AxisControlRow(
            panel, "A", "Movement (Deg)", 
            a_direction_opts,
            self.direction_to_text(a_dir, a_direction_opts),
            a_speed,
            self.log,
            self.robot_controller,
            a_steps_per_unit
        )
        self.a_axis.pack(fill=tk.X, pady=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=10)
        
        # Grip control
        self.grip = GripControlRow(panel, self.log, self.robot_controller)
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
        """Create right panel: Inverse kinematics."""
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
        
        # Title section
        tk.Label(
            panel,
            text="Move End Effector to Position",
            font=('Arial', 10, 'bold'),
            bg='#ffffff'
        ).pack(pady=(5, 15))
        
        # Input frame
        input_frame = tk.Frame(panel, bg='#ffffff')
        input_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # X position input
        x_row = tk.Frame(input_frame, bg='#ffffff')
        x_row.pack(fill=tk.X, pady=5)
        tk.Label(x_row, text="X Position (cm):", width=15, anchor='w', bg='#ffffff').pack(side=tk.LEFT)
        self.ik_x_entry = tk.Entry(x_row, width=12, font=('Arial', 10))
        self.ik_x_entry.pack(side=tk.LEFT, padx=5)
        self.ik_x_entry.insert(0, "0")
        
        # Y position input
        y_row = tk.Frame(input_frame, bg='#ffffff')
        y_row.pack(fill=tk.X, pady=5)
        tk.Label(y_row, text="Y Position (cm):", width=15, anchor='w', bg='#ffffff').pack(side=tk.LEFT)
        self.ik_y_entry = tk.Entry(y_row, width=12, font=('Arial', 10))
        self.ik_y_entry.pack(side=tk.LEFT, padx=5)
        self.ik_y_entry.insert(0, "0")
        
        # Speed input
        speed_row = tk.Frame(input_frame, bg='#ffffff')
        speed_row.pack(fill=tk.X, pady=5)
        tk.Label(speed_row, text="Speed (steps/s):", width=15, anchor='w', bg='#ffffff').pack(side=tk.LEFT)
        self.ik_speed_entry = tk.Entry(speed_row, width=12, font=('Arial', 10))
        self.ik_speed_entry.pack(side=tk.LEFT, padx=5)
        self.ik_speed_entry.insert(0, "1000")
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=20, padx=20)
        
        # Results display
        results_frame = tk.LabelFrame(panel, text="Calculated Angles", bg='#ffffff', font=('Arial', 9, 'bold'))
        results_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # X angle display
        x_angle_row = tk.Frame(results_frame, bg='#ffffff')
        x_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(x_angle_row, text="X Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.ik_x_angle_label = tk.Label(x_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#0066cc')
        self.ik_x_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Z angle display
        z_angle_row = tk.Frame(results_frame, bg='#ffffff')
        z_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(z_angle_row, text="Z Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.ik_z_angle_label = tk.Label(z_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#0066cc')
        self.ik_z_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Distance display
        dist_row = tk.Frame(results_frame, bg='#ffffff')
        dist_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(dist_row, text="Distance:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.ik_dist_label = tk.Label(dist_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9), fg='#666666')
        self.ik_dist_label.pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=20, padx=20)
        
        # Buttons
        button_frame = tk.Frame(panel, bg='#ffffff')
        button_frame.pack(pady=10)
        
        # Test button
        tk.Button(
            button_frame,
            text="Test IK",
            font=('Arial', 10),
            width=12,
            height=2,
            command=self.on_test_ik,
            bg='#e0e0e0',
            activebackground='#d0d0d0'
        ).pack(side=tk.LEFT, padx=5)
        
        # Move button (initially disabled until zeroised)
        self.move_to_position_button = tk.Button(
            button_frame,
            text="Move to Position",
            font=('Arial', 10, 'bold'),
            width=15,
            height=2,
            command=self.on_move_to_position,
            bg='#ccddff',
            activebackground='#aaccff',
            state=tk.DISABLED
        )
        self.move_to_position_button.pack(side=tk.LEFT, padx=5)
        
        # Go to Zero button (initially disabled until all axes are homed)
        self.go_to_zero_button = tk.Button(
            button_frame,
            text="Go to Zero",
            font=('Arial', 10),
            width=12,
            height=2,
            command=self.on_go_to_zero,
            bg='#ccffcc',
            activebackground='#aaffaa',
            state=tk.DISABLED
        )
        self.go_to_zero_button.pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=15, padx=20)
        
        # Zeroised status indicator
        zero_status_frame = tk.Frame(panel, bg='#ffffff')
        zero_status_frame.pack(pady=5)
        tk.Label(zero_status_frame, text="Zeroised:", font=('Arial', 9, 'bold'), bg='#ffffff').pack(side=tk.LEFT, padx=5)
        self.zeroised_indicator = tk.Canvas(zero_status_frame, width=25, height=25, bg='#ffffff', highlightthickness=1, highlightbackground='#888888')
        self.zeroised_indicator.pack(side=tk.LEFT, padx=5)
        self.zeroised_indicator.create_oval(5, 5, 20, 20, fill='#cccccc', outline='#888888', tags='indicator')
        tk.Label(zero_status_frame, text="(OFF)", font=('Arial', 8, 'italic'), fg='#888888', bg='#ffffff').pack(side=tk.LEFT, padx=2)
        
        # Info label
        info_label = tk.Label(
            panel,
            text="(0,0) = Arms fully extended down\nL1=22.8cm, L2=13.65cm | X: ±75°, Z: ±140°",
            font=('Arial', 8, 'italic'),
            fg='#888888',
            bg='#ffffff',
            justify=tk.CENTER
        )
        info_label.pack(pady=(10, 5))
    
    def create_status_panel(self, parent):
        """Create status panel showing stopper and homing status."""
        status_frame = tk.Frame(parent, relief=tk.GROOVE, borderwidth=2, bg='#ffffff')
        status_frame.grid(row=1, column=0, columnspan=2, sticky='ew', padx=0, pady=(5, 5))
        
        # Configure grid for 4 columns (one per axis)
        for i in range(4):
            status_frame.columnconfigure(i, weight=1, uniform="axis")
        
        axes = ['Y', 'X', 'Z', 'A']
        
        # Stopper status indicators
        self.stopper_indicators = {}
        self.homing_indicators = {}
        self.remain_entries = {}
        
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
            
            # Remain values
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
            tk.Label(remain_values, text="up" if axis == 'Y' else "CW", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            upper_entry = tk.Entry(remain_values, width=6, font=('Arial', 7))
            upper_entry.pack(side=tk.LEFT, padx=2)
            upper_entry.config(state='readonly')
            
            tk.Label(remain_values, text="down" if axis == 'Y' else "CCW", font=('Arial', 8), bg='#ffffff').pack(side=tk.LEFT)
            lower_entry = tk.Entry(remain_values, width=6, font=('Arial', 7))
            lower_entry.pack(side=tk.LEFT, padx=2)
            lower_entry.config(state='readonly')
            
            # Store Entry widgets for later updates
            self.remain_entries[axis] = {'upper': upper_entry, 'lower': lower_entry}
            
      
            upper_entry.config(state='normal')
            upper_entry.delete(0, tk.END)
            upper_entry.insert(0, "0") 
            upper_entry.config(state='readonly')
                
            lower_entry.config(state='normal')
            lower_entry.delete(0, tk.END)
            lower_entry.insert(0, "0") 
            lower_entry.config(state='readonly')
    
    def create_action_buttons(self, parent):
        """Create bottom action button row."""
        button_frame = tk.Frame(parent, bg='#f5f5f5')
        button_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=(5, 5))
        
        button_config = {
            'width': 12,
            'height': 2,
            'font': ('Arial', 10)
        }
        
        tk.Button(button_frame, text="Exit", command=self.on_exit, bg='#ffcccc', activebackground='#ffaaaa', **button_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Home", command=self.on_home, bg='#ccffcc', activebackground='#aaffaa', **button_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="Estop", command=self.on_estop, bg='#ffcccc', activebackground='#ffaaaa', **button_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="CLR", command=self.on_clr, bg='#ffffcc', activebackground='#ffffaa', **button_config).pack(side=tk.LEFT, padx=5)
        
        # Tech button with toggle state
        self.tech_button = tk.Button(
            button_frame, 
            text="Tech: OFF", 
            command=self.on_tech, 
            bg='#e0e0e0',
            activebackground='#d0d0d0',
            **button_config
        )
        self.tech_button.pack(side=tk.LEFT, padx=5)
        
        tk.Button(button_frame, text="Sync", command=self.on_sync, bg='#ccddff', activebackground='#aaccff', **button_config).pack(side=tk.LEFT, padx=5)
    
    def create_log_panel(self, parent):
        """Create log panel at the bottom."""
        self.log_panel = LogPanel(parent)
        self.log_panel.grid(row=3, column=0, columnspan=2, sticky='nsew', pady=(5, 0))
    
    # Visual update methods
    
    def update_stopper_indicator(self, axis, is_pressed):
        """Update stopper indicator visual."""
        if axis in self.stopper_indicators:
            color = '#ff4444' if is_pressed else '#44ff44'
            self.stopper_indicators[axis].itemconfig('indicator', fill=color)
            self.root.update()
    
    def update_homing_indicator(self, axis, is_homed):
        """Update homing indicator visual."""
        if axis in self.homing_indicators:
            color = '#44ff44' if is_homed else '#cccccc'
            self.homing_indicators[axis].itemconfig('indicator', fill=color)
            self.root.update()
    
    def update_zeroised_indicator(self, is_zeroised):
        """Update zeroised indicator visual."""
        color = '#44ff44' if is_zeroised else '#cccccc'
        self.zeroised_indicator.itemconfig('indicator', fill=color)
        self.root.update()
    
    def check_and_enable_go_to_zero(self):
        """Check if all axes are homed and enable Go to Zero button if true."""
        all_homed = (
            self.robot_controller.Y_homing_status and
            self.robot_controller.X_homing_status and
            self.robot_controller.Z_homing_status and
            self.robot_controller.A_homing_status
        )
        
        if all_homed:
            self.go_to_zero_button.config(state=tk.NORMAL)
            self.log("[System] Go to Zero button ENABLED - all axes homed ✓")
        else:
            self.go_to_zero_button.config(state=tk.DISABLED)
    
    def update_remain_values(self,home=False):
        """Update all axis remain values display."""
        if home == True:
            self.robot_controller.reset_remain_limits()  # Refresh remain limits from robot after homing

        for axis in ['Y', 'X', 'Z', 'A']:
            if axis in self.remain_entries:
                # Check if remain_limits exists for this axis
                if hasattr(self.robot_controller, 'remain_limits') and axis in self.robot_controller.remain_limits:

                    if axis == 'X':
                        max_val = self.robot_controller.remain_limits[axis]["max"]
                        min_val = self.robot_controller.remain_limits[axis]["min"]
                    else:
                        max_val = self.robot_controller.remain_limits[axis]["min"]
                        min_val = self.robot_controller.remain_limits[axis]["max"]
                    
                    # Update upper entry (CW or Up direction)
                    upper_entry = self.remain_entries[axis]['upper']
                    upper_entry.config(state='normal')
                    upper_entry.delete(0, tk.END)
                    upper_entry.insert(0, f"{max_val:.1f}")
                    upper_entry.config(state='readonly')
                    
                    # Update lower entry (CCW or Down direction)
                    lower_entry = self.remain_entries[axis]['lower']
                    lower_entry.config(state='normal')
                    lower_entry.delete(0, tk.END)
                    lower_entry.insert(0, f"{min_val:.1f}")
                    lower_entry.config(state='readonly')
        
        self.root.update()
    
    def update_all_stopper_status(self):
        """Query and update all stopper status visuals."""
        status = self.robot_controller.query_all_stopper_status()
        for axis, is_pressed in status.items():
            self.update_stopper_indicator(axis, is_pressed)
    
    # Button callbacks (delegate to controller)
    
    def on_go_pressed(self):
        """Handle GO button press."""
        self.log("[GO] Starting movement execution...")
        self.root.update()
        
        results = self.robot_controller.execute_all_movements()
        
        # Update visuals based on results
        for axis, result in results.items():
            self.update_stopper_indicator(axis, self.robot_controller.__dict__[f"{axis}_stopper_status"])
            self.update_remain_values()
        
        if results:
            self.log(f"[GO] Completed {len(results)} axis movements")
        else:
            self.log("[GO] No active axis commands to execute")
        
        self.root.update()
        
        # Reset all axis buttons
        self.x_axis.reset_button()
        self.y_axis.reset_button()
        self.z_axis.reset_button()
        self.a_axis.reset_button()
    
    def on_home(self):
        """Handle Home button press."""
        if not self.robot_controller.link:
            self.log("[Home] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[Home] Starting homing sequence for all axes")
        self.root.update()
        
        # Home Y axis
        Y_homing = "Y 20000 1000"
        Y_backoff = "Y -200 1000"
        status_y = self.robot_controller.home_axis("Y", Y_homing, Y_backoff)
        
        # Update visuals
        self.update_stopper_indicator("Y", self.robot_controller.Y_stopper_status)
        self.update_homing_indicator("Y", self.robot_controller.Y_homing_status)
        
        self.log(f"[Home] Y: {status_y}")
        self.root.update()

        # Home X axis (rotational - degrees)
        X_homing = "X -36000 1000"      # Move CW towards stopper (360 degrees = 36000 steps typically)
        X_backoff = "X 500 1000"      # Back off from stopper
        status_x = self.robot_controller.home_axis("X", X_homing, X_backoff)
        
        # Update visuals for X
        self.update_stopper_indicator("X", self.robot_controller.X_stopper_status)
        self.update_homing_indicator("X", self.robot_controller.X_homing_status)
        
        self.log(f"[Home] X: {status_x}")
        self.root.update()

        # Home Z axis (rotational - degrees)
        Z_homing = "Z 36000 1000"      # Move CW towards stopper
        Z_backoff = "Z -500 1000"      # Back off from stopper
        status_z = self.robot_controller.home_axis("Z", Z_homing, Z_backoff)
        
        # Update visuals for Z
        self.update_stopper_indicator("Z", self.robot_controller.Z_stopper_status)
        self.update_homing_indicator("Z", self.robot_controller.Z_homing_status)
        
        self.log(f"[Home] Z: {status_z}")
        self.root.update()
        
        # Home A axis (rotational - degrees)
        A_homing = "A 36000 1000"      # Move CW towards stopper
        A_backoff = "A -500 1000"      # Back off from stopper
        status_a = self.robot_controller.home_axis("A", A_homing, A_backoff)
        
        # Update visuals for A
        self.update_stopper_indicator("A", self.robot_controller.A_stopper_status)
        self.update_homing_indicator("A", self.robot_controller.A_homing_status)
        
        self.log(f"[Home] A: {status_a}")
        self.root.update()
        
        # Summary
        self.update_remain_values()
        self.log(f"[Home] Homing complete - Y:{status_y}, X:{status_x}, Z:{status_z}, A:{status_a}")
        
        # Check if all axes homed and enable Go to Zero button if ready
        self.check_and_enable_go_to_zero()
        
        self.root.update()
        
        # Zero out all axis commands to prevent unwanted data
        self.robot_controller.update_axis_command("Y", "")
        self.robot_controller.update_axis_command("X", "")
        self.robot_controller.update_axis_command("Z", "")
        self.robot_controller.update_axis_command("A", "")
        self.log("[Home] Axis commands cleared")
        self.root.update()
            
    def on_sync(self):
        """Handle Sync button press."""
        self.robot_controller.sync()
        self.root.update()
    
    def on_estop(self):
        """Handle Estop button press."""
        self.robot_controller.estop()
        self.root.update()
    
    def on_clr(self):
        """Handle CLR button press."""
        self.robot_controller.clear_estop()
        self.root.update()
    
    def on_tech(self):
        """Handle Tech button press - toggles technician mode."""
        # Toggle tech mode state
        self.tech_mode_enabled = not self.tech_mode_enabled
        
        # Update button appearance
        if self.tech_mode_enabled:
            self.tech_button.config(text="Tech: ON", bg='#ffaa00', activebackground='#ff8800')
            self.log("[TECH] WARNING: Technician mode ENABLED - Stopper protection bypassed!")
        else:
            self.tech_button.config(text="Tech: OFF", bg='#e0e0e0', activebackground='#d0d0d0')
            self.log("[TECH] Technician mode DISABLED - Normal operation")
        
        # Send command to robot
        self.robot_controller.set_tech_mode(self.tech_mode_enabled)
        self.root.update()
    
    def on_test_ik(self):
        """Handle Test IK button press - calculate without moving."""
        try:
            x = float(self.ik_x_entry.get())
            y = float(self.ik_y_entry.get())
        except ValueError:
            self.log("[IK] ERROR: Invalid X or Y value. Please enter numbers.")
            return
        
        self.log(f"[IK] Testing position: ({x:.2f}, {y:.2f}) cm")
        self.root.update()
        
        # Calculate IK
        result = self.robot_controller.inverse_kinematics(x, y)
        
        if result['success']:
            # Update display labels with direction
            x_dir = result.get('x_angle_direction', '')
            z_dir = result.get('z_angle_direction', '')
            self.ik_x_angle_label.config(text=f"{result['x_angle_deg']:.2f}° ({x_dir})", fg='#0066cc')
            self.ik_z_angle_label.config(text=f"{result['z_angle_deg']:.2f}° ({z_dir})", fg='#0066cc')
            
            # Calculate and show distance
            distance = math.sqrt(x**2 + y**2)
            self.ik_dist_label.config(text=f"{distance:.2f} cm", fg='#666666')
            
            self.log(f"[IK] ✓ {result['message']}")
            self.log(f"[IK] X: {result['x_steps']} steps, Z: {result['z_steps']} steps")
        else:
            # Show error
            self.ik_x_angle_label.config(text="--", fg='#ff0000')
            self.ik_z_angle_label.config(text="--", fg='#ff0000')
            self.ik_dist_label.config(text="Out of reach", fg='#ff0000')
            self.log(f"[IK] ✗ {result['message']}")
        
        self.root.update()
    
    def on_move_to_position(self):
        """Handle Move to Position button press - calculate and move."""
        if not self.robot_controller.link:
            self.log("[IK] ERROR: Not connected to robot")
            self.root.update()
            return
        
        try:
            x = float(self.ik_x_entry.get())
            y = float(self.ik_y_entry.get())
            speed = int(self.ik_speed_entry.get())
        except ValueError:
            self.log("[IK] ERROR: Invalid input values. Please enter numbers.")
            return
        
        self.log(f"[IK] Moving to position: ({x:.2f}, {y:.2f}) cm at {speed} steps/s")
        self.root.update()
        
        # Move to position
        result = self.robot_controller.move_to_position(x, y, speed)
        
        if result['success']:
            # Update display labels with direction
            x_dir = result.get('x_angle_direction', '')
            z_dir = result.get('z_angle_direction', '')
            self.ik_x_angle_label.config(text=f"{result['x_angle_deg']:.2f}° ({x_dir})", fg='#00cc00')
            self.ik_z_angle_label.config(text=f"{result['z_angle_deg']:.2f}° ({z_dir})", fg='#00cc00')
            
            # Calculate and show distance
            distance = math.sqrt(x**2 + y**2)
            self.ik_dist_label.config(text=f"{distance:.2f} cm", fg='#00cc00')
            
            self.log(f"[IK] ✓ Movement complete!")
            
            # Update stopper status after movement
            if 'movement_results' in result:
                for axis, move_result in result['movement_results'].items():
                    stopper_status = self.robot_controller.__dict__.get(f"{axis}_stopper_status", False)
                    self.update_stopper_indicator(axis, stopper_status)
        else:
            # Show error
            self.ik_x_angle_label.config(text="--", fg='#ff0000')
            self.ik_z_angle_label.config(text="--", fg='#ff0000')
            self.ik_dist_label.config(text="Error", fg='#ff0000')
            self.log(f"[IK] ✗ {result['message']}")
        
        self.root.update()
    
    def on_go_to_zero(self):
        """Handle Go to Zero button press - move to (0,0) position."""
        if not self.robot_controller.link:
            self.log("[Zero] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[Zero] Moving to zero position (0, 0)...")
        self.root.update()
        
        # Call controller method
        success = self.robot_controller.go_to_zero()
        
        # Update zeroised indicator based on success
        self.update_zeroised_indicator(success)
        
        if success:
            self.log("[Zero] ✓ Successfully zeroised")
            # Enable Move to Position button after successful zeroising
            self.move_to_position_button.config(state=tk.NORMAL)
            self.log("[System] Move to Position button ENABLED - robot zeroised ✓")
        else:
            self.log("[Zero] ✗ Zeroising failed")
            # Keep Move to Position button disabled
            self.move_to_position_button.config(state=tk.DISABLED)
        
        self.root.update()
    
    def on_exit(self):
        """Handle Exit button press."""
        self.log("[System] Exit pressed - closing application")
        self.root.update()
        
        # Disable tech mode before exit for safety
        if self.tech_mode_enabled and self.robot_controller.link:
            self.log("[System] Disabling tech mode before exit...")
            self.robot_controller.set_tech_mode(False)
        
        self.robot_controller.cleanup()
        self.root.destroy()