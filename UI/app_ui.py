"""
SCARA Robot Controller - UI Layer

This module contains all Tkinter UI components and visual elements.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
from datetime import datetime
import math
from camera_view import CameraCapture, CameraPanel


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


class TicTacToeControlPanel(tk.Frame):
    """Tic-Tac-Toe control panel for marker status and future board actions."""

    PANEL_BG = '#ffffff'
    BUTTON_BG = '#0f5d78'
    BUTTON_ACTIVE_BG = '#0b4c62'
    BUTTON_FG = '#ffffff'

    def __init__(self, parent, marker_status_callback, log_callback):
        super().__init__(parent, relief=tk.GROOVE, borderwidth=2, bg=self.PANEL_BG, padx=15, pady=15)
        self.marker_status_callback = marker_status_callback
        self.log_callback = log_callback

        tk.Label(
            self,
            text="Tic tac tow control",
            font=('Arial', 28),
            bg=self.PANEL_BG,
            anchor='w'
        ).pack(side=tk.TOP, fill=tk.X, pady=(0, 12))

        top_frame = tk.Frame(self, bg=self.PANEL_BG)
        top_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 15))
        top_frame.columnconfigure(0, weight=1)
        top_frame.columnconfigure(1, weight=1)
        top_frame.columnconfigure(2, weight=1)

        self.marker_number_entry = tk.Entry(
            top_frame,
            font=('Arial', 16),
            width=14,
            justify=tk.CENTER,
            relief=tk.SOLID,
            borderwidth=2
        )
        self.marker_number_entry.grid(row=0, column=0, padx=8, sticky='ew')
        self._add_entry_placeholder(self.marker_number_entry, "Marker number")

        self.status_button = tk.Button(
            top_frame,
            text="Status",
            font=('Arial', 24),
            width=11,
            command=self.on_status_pressed,
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            activebackground=self.BUTTON_ACTIVE_BG,
            activeforeground=self.BUTTON_FG,
            relief=tk.RAISED,
            borderwidth=4
        )
        self.status_button.grid(row=0, column=1, padx=8, sticky='ew')

        self.marker_status_var = tk.StringVar(value="Marker status")
        self.marker_status_label = tk.Label(
            top_frame,
            textvariable=self.marker_status_var,
            font=('Arial', 16),
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            relief=tk.RAISED,
            borderwidth=3,
            width=16
        )
        self.marker_status_label.grid(row=0, column=2, padx=8, sticky='ew')

        self.board_frame = tk.Frame(self, bg=self.PANEL_BG)
        self.board_frame.pack(side=tk.TOP, pady=(5, 20))
        self.board_cells = []
        for row in range(3):
            row_cells = []
            for col in range(3):
                cell_index = row * 3 + col
                label = tk.Label(
                    self.board_frame,
                    text=f"{cell_index}/{cell_index + 15}",
                    font=('Arial', 11, 'bold'),
                    width=10,
                    height=4,
                    bg='#f7f7f7',
                    fg='#000000',
                    relief=tk.SOLID,
                    borderwidth=2
                )
                label.grid(row=row, column=col, sticky='nsew')
                row_cells.append(label)
            self.board_cells.append(row_cells)

        bottom_frame = tk.Frame(self, bg=self.PANEL_BG)
        bottom_frame.pack(side=tk.TOP, fill=tk.X)

        self.your_turn_button = tk.Button(
            bottom_frame,
            text="You turn",
            font=('Arial', 24),
            width=12,
            command=self.on_your_turn_pressed,
            bg=self.BUTTON_BG,
            fg=self.BUTTON_FG,
            activebackground=self.BUTTON_ACTIVE_BG,
            activeforeground=self.BUTTON_FG,
            relief=tk.RAISED,
            borderwidth=4
        )
        self.your_turn_button.pack(side=tk.LEFT, padx=10, pady=5)

    def _add_entry_placeholder(self, entry, placeholder):
        entry.insert(0, placeholder)
        entry.config(fg='#ffffff', bg=self.BUTTON_BG)

        def on_focus_in(_event):
            if entry.get() == placeholder:
                entry.delete(0, tk.END)
                entry.config(fg='#000000', bg='#ffffff')

        def on_focus_out(_event):
            if not entry.get().strip():
                entry.insert(0, placeholder)
                entry.config(fg='#ffffff', bg=self.BUTTON_BG)

        entry.bind('<FocusIn>', on_focus_in)
        entry.bind('<FocusOut>', on_focus_out)

    def on_status_pressed(self):
        marker_text = self.marker_number_entry.get().strip()
        if marker_text == "Marker number" or not marker_text:
            self.marker_status_var.set("Enter marker #")
            self.log_callback("[TicTacToe] Marker number is required")
            return

        try:
            marker_number = int(marker_text)
        except ValueError:
            self.marker_status_var.set("Invalid marker")
            self.log_callback(f"[TicTacToe] Invalid marker number: {marker_text}")
            return

        result = self.marker_status_callback(marker_number)
        self.marker_status_var.set(str(result))
        self.log_callback(f"[TicTacToe] Marker {marker_number} status: {result}")

    def on_your_turn_pressed(self):
        self.log_callback("[TicTacToe] Your turn button pressed - logic not implemented yet")


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
        self.root.geometry("2200x1400")
        self.root.minsize(2200, 1400)
        
        # Tech mode state
        self.tech_mode_enabled = False
        
        # Configure root grid weights for resizing
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Main container
        main_container = tk.Frame(self.root, bg='#f5f5f5')
        main_container.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
        main_container.columnconfigure(0, weight=1)  # Camera panel
        main_container.columnconfigure(1, weight=1)  # Axis Direct move
        main_container.columnconfigure(2, weight=1)  # Inverse kinematics
        main_container.rowconfigure(0, weight=3)
        main_container.rowconfigure(1, weight=0)
        main_container.rowconfigure(2, weight=0)
        main_container.rowconfigure(3, weight=2)
        
        # Initialize camera (use index 1 for USB camera, 0 for integrated)
        self.camera_capture = CameraCapture(camera_index=1, width=640, height=480)
        
        # Create panels
        self.create_camera_panel(main_container)
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
    
    def create_camera_panel(self, parent):
        """Create camera panel on the left."""
        self.camera_panel = CameraPanel(parent, self.camera_capture, update_interval=30, parent_app=self)
        self.camera_panel.grid(row=0, column=0, sticky='nsew', padx=(0, 5), pady=(0, 5))
    
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
        panel.grid(row=0, column=1, sticky='nsew', padx=5, pady=(0, 5))
        
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

        # Tic-Tac-Toe control panel
        self.tictactoe_panel = TicTacToeControlPanel(
            panel,
            marker_status_callback=self.get_marker_status,
            log_callback=self.log
        )
        self.tictactoe_panel.pack(fill=tk.BOTH, expand=True, pady=(10, 0))
    
    def get_marker_status(self, marker_number):
        """Return marker status using the camera panel helper."""
        if not hasattr(self, 'camera_panel') or self.camera_panel is None:
            return "Camera not ready"
        return self.camera_panel.marker_status(marker_number)

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
        panel.grid(row=0, column=2, sticky='nsew', padx=(5, 0), pady=(0, 5))
        
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

        # Marker position picker (load marker X/Y into IK inputs)
        marker_row = tk.Frame(input_frame, bg='#ffffff')
        marker_row.pack(fill=tk.X, pady=5)
        tk.Label(marker_row, text="Marker preset:", width=15, anchor='w', bg='#ffffff').pack(side=tk.LEFT)

        self.marker_position_var = tk.StringVar()
        self.marker_position_dropdown = ttk.Combobox(
            marker_row,
            textvariable=self.marker_position_var,
            width=25,
            state='readonly'
        )
        self.marker_position_dropdown.pack(side=tk.LEFT, padx=5)

        self.upload_marker_xy_button = tk.Button(
            marker_row,
            text="Upload XY",
            font=('Arial', 9),
            command=self.on_upload_marker_xy,
            bg='#ddeeff',
            activebackground='#cce0ff'
        )
        self.upload_marker_xy_button.pack(side=tk.LEFT, padx=5)
        
        # Speed input
        speed_row = tk.Frame(input_frame, bg='#ffffff')
        speed_row.pack(fill=tk.X, pady=5)
        tk.Label(speed_row, text="Speed (steps/s):", width=15, anchor='w', bg='#ffffff').pack(side=tk.LEFT)
        self.ik_speed_entry = tk.Entry(speed_row, width=12, font=('Arial', 10))
        self.ik_speed_entry.pack(side=tk.LEFT, padx=5)
        self.ik_speed_entry.insert(0, "2000")

        self.marker_position_map = {}
        self.refresh_marker_position_dropdown()
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=20, padx=20)
        
        # First row: Calculated Angles and Sec calculated angles side by side
        first_row_container = tk.Frame(panel, bg='#ffffff')
        first_row_container.pack(fill=tk.X, padx=20, pady=10)
        first_row_container.columnconfigure(0, weight=1)
        first_row_container.columnconfigure(1, weight=1)
        
        # Calculated Angles (left side)
        results_frame = tk.LabelFrame(first_row_container, text="Calculated Angles", bg='#ffffff', font=('Arial', 9, 'bold'))
        results_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
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
        
        # Sec calculated angles (right side)
        sec_results_frame = tk.LabelFrame(first_row_container, text="Sec calculated angles", bg='#ffffff', font=('Arial', 9, 'bold'))
        sec_results_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Sec X angle display
        sec_x_angle_row = tk.Frame(sec_results_frame, bg='#ffffff')
        sec_x_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(sec_x_angle_row, text="X Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.sec_x_angle_label = tk.Label(sec_x_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#cc6600')
        self.sec_x_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Sec Z angle display
        sec_z_angle_row = tk.Frame(sec_results_frame, bg='#ffffff')
        sec_z_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(sec_z_angle_row, text="Z Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.sec_z_angle_label = tk.Label(sec_z_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#cc6600')
        self.sec_z_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Sec distance display
        sec_dist_row = tk.Frame(sec_results_frame, bg='#ffffff')
        sec_dist_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(sec_dist_row, text="Distance:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.sec_dist_label = tk.Label(sec_dist_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9), fg='#999966')
        self.sec_dist_label.pack(side=tk.LEFT, padx=5)
        
        # Second row: Movement angles and Last position side by side
        second_row_container = tk.Frame(panel, bg='#ffffff')
        second_row_container.pack(fill=tk.X, padx=20, pady=10)
        second_row_container.columnconfigure(0, weight=1)
        second_row_container.columnconfigure(1, weight=1)
        
        # Movement angles (left side)
        movement_frame = tk.LabelFrame(second_row_container, text="Movement angles", bg='#ffffff', font=('Arial', 9, 'bold'))
        movement_frame.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        
        # Movement X angle display
        mov_x_angle_row = tk.Frame(movement_frame, bg='#ffffff')
        mov_x_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(mov_x_angle_row, text="X Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.mov_x_angle_label = tk.Label(mov_x_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#00aa00')
        self.mov_x_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Movement Z angle display
        mov_z_angle_row = tk.Frame(movement_frame, bg='#ffffff')
        mov_z_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(mov_z_angle_row, text="Z Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.mov_z_angle_label = tk.Label(mov_z_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#00aa00')
        self.mov_z_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Movement distance display
        mov_dist_row = tk.Frame(movement_frame, bg='#ffffff')
        mov_dist_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(mov_dist_row, text="Distance:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.mov_dist_label = tk.Label(mov_dist_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9), fg='#669966')
        self.mov_dist_label.pack(side=tk.LEFT, padx=5)
        
        # Last position (right side)
        last_pos_frame = tk.LabelFrame(second_row_container, text="Last position", bg='#ffffff', font=('Arial', 9, 'bold'))
        last_pos_frame.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        
        # Last X angle display
        last_x_angle_row = tk.Frame(last_pos_frame, bg='#ffffff')
        last_x_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(last_x_angle_row, text="X Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.last_x_angle_label = tk.Label(last_x_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#886600')
        self.last_x_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Last Z angle display
        last_z_angle_row = tk.Frame(last_pos_frame, bg='#ffffff')
        last_z_angle_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(last_z_angle_row, text="Z Axis Angle:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.last_z_angle_label = tk.Label(last_z_angle_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9, 'bold'), fg='#886600')
        self.last_z_angle_label.pack(side=tk.LEFT, padx=5)
        
        # Last distance display
        last_dist_row = tk.Frame(last_pos_frame, bg='#ffffff')
        last_dist_row.pack(fill=tk.X, pady=3, padx=10)
        tk.Label(last_dist_row, text="Distance:", width=12, anchor='w', bg='#ffffff', font=('Arial', 9)).pack(side=tk.LEFT)
        self.last_dist_label = tk.Label(last_dist_row, text="--", width=15, anchor='w', bg='#ffffff', font=('Arial', 9), fg='#888888')
        self.last_dist_label.pack(side=tk.LEFT, padx=5)
        
        # Separator
        ttk.Separator(panel, orient='horizontal').pack(fill=tk.X, pady=20, padx=20)
        
        # Item Detected section
        item_detected_frame = tk.LabelFrame(panel, text="Item Detected", bg='#ffffff', font=('Arial', 10, 'bold'))
        item_detected_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Create table for detected items
        table_frame = tk.Frame(item_detected_frame, bg='#ffffff')
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Define columns
        columns = ("ID", "Camera X", "Camera Y", "Marker 0->X", "Marker 0->Y", "Robot X", "Robot Y")
        self.item_table = ttk.Treeview(table_frame, columns=columns, show='headings', height=3)
        
        # Configure column headings and widths
        col_widths = [50, 75, 75, 85, 85, 75, 75]
        for col, width in zip(columns, col_widths):
            self.item_table.heading(col, text=col)
            self.item_table.column(col, width=width, anchor='center')
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.item_table.yview)
        self.item_table.configure(yscroll=scrollbar.set)
        
        self.item_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Configure tag colors for different items
        self.item_table.tag_configure('green', background='#ccffcc')
        self.item_table.tag_configure('blue', background='#ccccff')
        self.item_table.tag_configure('yellow', background='#ffffcc')
        self.item_table.tag_configure('red', background='#ffcccc')
        self.item_table.tag_configure('black', background='#d9d9d9')
        self.item_table.tag_configure('pink', background='#ffd9ef')
        self.item_table.tag_configure('brown', background='#e6ccb3')
        
        # Buttons below the table
        item_buttons_frame = tk.Frame(item_detected_frame, bg='#ffffff')
        item_buttons_frame.pack(pady=5)

        color_options = ["Green", "Yellow", "Blue", "Red", "Black", "Pink", "Brown"]

        tk.Label(
            item_buttons_frame,
            text="Pick",
            font=('Arial', 9, 'bold'),
            bg='#ffffff'
        ).pack(side=tk.LEFT, padx=(5, 3))

        self.pick_color_combo = ttk.Combobox(
            item_buttons_frame,
            values=color_options,
            width=9,
            state='readonly'
        )
        self.pick_color_combo.set("Green")
        self.pick_color_combo.pack(side=tk.LEFT, padx=(0, 8))

        tk.Label(
            item_buttons_frame,
            text="Put it on",
            font=('Arial', 9, 'bold'),
            bg='#ffffff'
        ).pack(side=tk.LEFT, padx=(0, 3))

        self.place_color_combo = ttk.Combobox(
            item_buttons_frame,
            values=color_options,
            width=9,
            state='readonly'
        )
        self.place_color_combo.set("Yellow")
        self.place_color_combo.pack(side=tk.LEFT, padx=(0, 8))

        self.pick_place_do_button = tk.Button(
            item_buttons_frame,
            text="Do",
            font=('Arial', 10, 'bold'),
            width=8,
            height=2,
            command=self.on_pick_and_place_colors,
            bg='#4472C4',
            fg='white',
            activebackground='#365a9e'
        )
        self.pick_place_do_button.pack(side=tk.LEFT, padx=5)
        
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
        
        # PullUP button (initially disabled until zeroised)
        self.pull_up_button = tk.Button(
            button_frame,
            text="PullUP",
            font=('Arial', 10, 'bold'),
            width=12,
            height=2,
            command=self.on_pull_up,
            bg='#ffffcc',
            activebackground='#ffffaa',
            state=tk.DISABLED
        )
        self.pull_up_button.pack(side=tk.LEFT, padx=5)
        
        # Put Down button (initially disabled until zeroised)
        self.put_down_button = tk.Button(
            button_frame,
            text="Put Down",
            font=('Arial', 10, 'bold'),
            width=12,
            height=2,
            command=self.on_put_down,
            bg='#ffddcc',
            activebackground='#ffccaa',
            state=tk.DISABLED
        )
        self.put_down_button.pack(side=tk.LEFT, padx=5)
        
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
        status_frame.grid(row=1, column=0, columnspan=3, sticky='ew', padx=0, pady=(5, 5))
        
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
        button_frame.grid(row=2, column=0, columnspan=3, sticky='ew', pady=(5, 5))
        
        # Configure equal weight for all columns to spread buttons evenly
        for i in range(6):
            button_frame.columnconfigure(i, weight=1, uniform='button')
        
        button_config = {
            'width': 12,
            'height': 2,
            'font': ('Arial', 10)
        }
        
        # Use grid layout for even distribution
        tk.Button(button_frame, text="Exit", command=self.on_exit, bg='#ffcccc', activebackground='#ffaaaa', **button_config).grid(row=0, column=0, padx=5, pady=0, sticky='ew')
        tk.Button(button_frame, text="Home", command=self.on_home, bg='#ccffcc', activebackground='#aaffaa', **button_config).grid(row=0, column=1, padx=5, pady=0, sticky='ew')
        tk.Button(button_frame, text="Estop", command=self.on_estop, bg='#ffcccc', activebackground='#ffaaaa', **button_config).grid(row=0, column=2, padx=5, pady=0, sticky='ew')
        tk.Button(button_frame, text="CLR", command=self.on_clr, bg='#ffffcc', activebackground='#ffffaa', **button_config).grid(row=0, column=3, padx=5, pady=0, sticky='ew')
        
        # Tech button with toggle state
        self.tech_button = tk.Button(
            button_frame, 
            text="Tech: OFF", 
            command=self.on_tech, 
            bg='#e0e0e0',
            activebackground='#d0d0d0',
            **button_config
        )
        self.tech_button.grid(row=0, column=4, padx=5, pady=0, sticky='ew')
        
        tk.Button(button_frame, text="Sync", command=self.on_sync, bg='#ccddff', activebackground='#aaccff', **button_config).grid(row=0, column=5, padx=5, pady=0, sticky='ew')
    
    def create_log_panel(self, parent):
        """Create log panel at the bottom."""
        self.log_panel = LogPanel(parent)
        self.log_panel.grid(row=3, column=0, columnspan=3, sticky='nsew', pady=(5, 0))
    
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
    
    def check_and_enable_go_to_zero(self) -> bool:
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
            return True
        else:
            self.go_to_zero_button.config(state=tk.DISABLED)
            return False
    
    def update_last_position_display(self):
        """Update last position display from robot controller."""
        last_pos = self.robot_controller.last_position
        
        if last_pos['is_valid']:
            # Update labels with last position data
            self.last_x_angle_label.config(
                text=f"{last_pos['x_angle_deg']:.2f}° ({last_pos['x_direction']})",
                fg='#886600'
            )
            self.last_z_angle_label.config(
                text=f"{last_pos['z_angle_deg']:.2f}° ({last_pos['z_direction']})",
                fg='#886600'
            )
            self.last_dist_label.config(
                text=f"{last_pos['distance']:.2f} cm",
                fg='#888888'
            )
        else:
            # No valid position yet
            self.last_x_angle_label.config(text="--", fg='#ff0000')
            self.last_z_angle_label.config(text="--", fg='#ff0000')
            self.last_dist_label.config(text="--", fg='#ff0000')
        
        self.root.update()
    
    def update_calculated_angles_display(self):
        """Update calculated angles display from robot controller."""
        abs_pos = self.robot_controller.absolute_position
        
        # Check if data has been calculated (distance > 0 means calculation was done)
        if abs_pos['distance'] > 0:
            # Pick color based on validity
            color = '#0066cc' if abs_pos['is_valid'] else '#ff0000'
            
            # Always show the values, use red for invalid (out of range)
            self.ik_x_angle_label.config(
                text=f"{abs_pos['x_angle_deg']:.2f}° ({abs_pos['x_direction']})",
                fg=color
            )
            self.ik_z_angle_label.config(
                text=f"{abs_pos['z_angle_deg']:.2f}° ({abs_pos['z_direction']})",
                fg=color
            )
            self.ik_dist_label.config(
                text=f"{abs_pos['distance']:.2f} cm",
                fg='#666666'
            )
        else:
            # No calculation done yet
            self.ik_x_angle_label.config(text="--", fg='#cccccc')
            self.ik_z_angle_label.config(text="--", fg='#cccccc')
            self.ik_dist_label.config(text="--", fg='#cccccc')
        
        self.root.update()
    
    def update_sec_calculated_angles_display(self):
        """Update secondary calculated angles display from robot controller."""
        sec_pos = self.robot_controller.sec_absolute_position
        
        # Check if data has been calculated (distance > 0 means calculation was done)
        if sec_pos['distance'] > 0:
            # Pick color based on validity
            color = '#cc6600' if sec_pos['is_valid'] else '#ff0000'
            
            # Always show the values, use red for invalid (out of range)
            self.sec_x_angle_label.config(
                text=f"{sec_pos['x_angle_deg']:.2f}° ({sec_pos['x_direction']})",
                fg=color
            )
            self.sec_z_angle_label.config(
                text=f"{sec_pos['z_angle_deg']:.2f}° ({sec_pos['z_direction']})",
                fg=color
            )
            self.sec_dist_label.config(
                text=f"{sec_pos['distance']:.2f} cm",
                fg='#999966'
            )
        else:
            # No calculation done yet
            self.sec_x_angle_label.config(text="--", fg='#cccccc')
            self.sec_z_angle_label.config(text="--", fg='#cccccc')
            self.sec_dist_label.config(text="--", fg='#cccccc')
        
        self.root.update()
    
    def update_movement_angles_display(self):
        """Update movement angles display from robot controller."""
        mov_angles = self.robot_controller.movement_angles
        
        # Check if data has been calculated (distance > 0 means calculation was done)
        if mov_angles['distance'] > 0:
            # Movement angles should always be valid during testing
            # (they represent the actual movement that would be executed)
            self.mov_x_angle_label.config(
                text=f"{mov_angles['x_angle_deg']:.2f}° ({mov_angles['x_direction']})",
                fg='#00aa00'
            )
            self.mov_z_angle_label.config(
                text=f"{mov_angles['z_angle_deg']:.2f}° ({mov_angles['z_direction']})",
                fg='#00aa00'
            )
            self.mov_dist_label.config(
                text=f"{mov_angles['distance']:.2f} cm",
                fg='#669966'
            )
        else:
            # No calculation done yet
            self.mov_x_angle_label.config(text="--", fg='#cccccc')
            self.mov_z_angle_label.config(text="--", fg='#cccccc')
            self.mov_dist_label.config(text="--", fg='#cccccc')
        
        self.root.update()
        self.root.update()
    
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
    
    def update_item_table(self, detected_objects):
        """Update the Item Detected table with detected colored objects.
        
        Args:
            detected_objects: dict with structure:
                {
                    'green': [(camera_x, camera_y, marker0_x, marker0_y, robot_x, robot_y), ...],
                    'blue': [...],
                    'yellow': [...]
                }
        """
        # Clear existing items
        for item in self.item_table.get_children():
            self.item_table.delete(item)
        
        # Add detected items
        for color in ['green', 'yellow', 'blue', 'red', 'black', 'pink', 'brown']:
            if color in detected_objects and detected_objects[color]:
                for obj_data in detected_objects[color]:
                    # obj_data is expected as (camera_x, camera_y, marker0_x, marker0_y, robot_x, robot_y)
                    # but Robot X/Y table columns are intentionally forced to marker0 values.
                    if len(obj_data) >= 6:
                        camera_x, camera_y, marker0_x, marker0_y, _robot_x, _robot_y = obj_data[:6]
                        values = (
                            color.capitalize(),
                            f"{camera_x:.1f}",
                            f"{camera_y:.1f}",
                            f"{marker0_x:.1f}",
                            f"{marker0_y:.1f}",
                            f"{marker0_x:.1f}",
                            f"{marker0_y:.1f}"
                        )
                        self.item_table.insert('', tk.END, values=values, tags=(color,))
    
    def get_item_position(self, color_name):
        """Get the robot position (x, y) of a detected item by color name.
        
        Args:
            color_name: Color name (e.g., 'Green', 'Blue', 'Yellow')
            
        Returns:
            tuple: (robot_x, robot_y) if found, None if not found
        """
        for item_id in self.item_table.get_children():
            values = self.item_table.item(item_id)['values']
            if values and values[0] == color_name:
                # Values are: (ID, Camera X, Camera Y, Marker 0->X, Marker 0->Y, Robot X, Robot Y)
                # Robot X is at index 5, Robot Y is at index 6
                try:
                    robot_x = float(values[5])
                    robot_y = float(values[6])
                    return (robot_x, robot_y)
                except (ValueError, IndexError):
                    return None
        return None

    def refresh_marker_position_dropdown(self):
        """Refresh marker dropdown values from configured calibration marker positions."""
        self.marker_position_map = {}
        marker_values = []

        marker_positions = {}
        if hasattr(self, 'camera_panel') and hasattr(self.camera_panel, 'calibration'):
            marker_positions = self.camera_panel.calibration.known_marker_positions

        for marker_id in sorted(marker_positions.keys()):
            x_val = marker_positions[marker_id]['x']
            y_val = marker_positions[marker_id]['y']
            label = f"Marker {marker_id} ({x_val:.1f}, {y_val:.1f})"
            marker_values.append(label)
            self.marker_position_map[label] = (x_val, y_val)

        self.marker_position_dropdown['values'] = marker_values
        if marker_values:
            self.marker_position_dropdown.set(marker_values[0])
        else:
            self.marker_position_dropdown.set('')

    def on_upload_marker_xy(self):
        """Load selected marker X/Y values into IK position inputs."""
        selected = self.marker_position_var.get()
        marker_xy = self.marker_position_map.get(selected)

        if marker_xy is None:
            self.log("[IK] No marker position selected")
            return

        marker_x, marker_y = marker_xy
        self.ik_x_entry.delete(0, tk.END)
        self.ik_x_entry.insert(0, f"{marker_x:.2f}")
        self.ik_y_entry.delete(0, tk.END)
        self.ik_y_entry.insert(0, f"{marker_y:.2f}")
        self.log(f"[IK] Loaded marker XY into inputs: ({marker_x:.2f}, {marker_y:.2f})")
    
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
        # Reset homing indicators before starting a new homing cycle.
        for axis in ['Y', 'X', 'Z', 'A']:
            self.update_homing_indicator(axis, False)

        if not self.robot_controller.link:
            self.log("[Home] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[Home] Starting homing sequence for all axes")
        self.root.update()
        
        # Home Y axis
        Y_homing = "Y 20000 2000"
        Y_backoff = "Y -200 2000"
        status_y = self.robot_controller.home_axis("Y", Y_homing, Y_backoff)
        
        # Update visuals
        self.update_stopper_indicator("Y", self.robot_controller.Y_stopper_status)
        self.update_homing_indicator("Y", self.robot_controller.Y_homing_status)
        
        self.log(f"[Home] Y: {status_y}")
        self.root.update()

        # Home X axis (rotational - degrees)
        X_homing = "X -36000 2000"      # Move CW towards stopper (360 degrees = 36000 steps typically)
        X_backoff = "X 500 2000"      # Back off from stopper
        status_x = self.robot_controller.home_axis("X", X_homing, X_backoff)
        
        # Update visuals for X
        self.update_stopper_indicator("X", self.robot_controller.X_stopper_status)
        self.update_homing_indicator("X", self.robot_controller.X_homing_status)
        
        self.log(f"[Home] X: {status_x}")
        self.root.update()

        # Home Z axis (rotational - degrees)
        Z_homing = "Z 36000 2000"      # Move CW towards stopper
        Z_backoff = "Z -500 2000"      # Back off from stopper
        status_z = self.robot_controller.home_axis("Z", Z_homing, Z_backoff)
        
        # Update visuals for Z
        self.update_stopper_indicator("Z", self.robot_controller.Z_stopper_status)
        self.update_homing_indicator("Z", self.robot_controller.Z_homing_status)
        
        self.log(f"[Home] Z: {status_z}")
        self.root.update()
        
        # Home A axis (rotational - degrees)
        A_homing = "A 36000 2000"      # Move CW towards stopper
        A_backoff = "A -500 2000"      # Back off from stopper
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
        status = self.check_and_enable_go_to_zero()
        if status:
            self.log("[Home] All axes homed successfully. Go to Zero button enabled.")
            self.log("[Home] the current  robot position is  (-9.82,12.001) position.")
            self.robot_controller.update_axis_position_after_home()
            # Update last position display
            self.update_last_position_display()
            # Enable Move to Position button after successful zeroising
            self.move_to_position_button.config(state=tk.NORMAL)
            self.log("[System] Move to Position button ENABLED - robot in home position  ✓")
            # Enable PullUP button after successful zeroising
            self.pull_up_button.config(state=tk.NORMAL)
            self.log("[System] PullUP button ENABLED - robot in home position  ✓")
            # Enable Put Down button after successful zeroising
            self.put_down_button.config(state=tk.NORMAL)
            self.log("[System] Put Down button ENABLED - robot in home position  ✓")

        
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
            self.log(f"[IK] ✓ {result['message']}")
            self.log(f"[IK] X: {result['x_steps']} steps, Z: {result['z_steps']} steps")
            
            # Update all position displays
            self.update_calculated_angles_display()
            self.update_sec_calculated_angles_display()
            self.update_movement_angles_display()
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
            # Update all position displays
            self.update_calculated_angles_display()
            self.update_sec_calculated_angles_display()
            self.update_movement_angles_display()
            self.update_last_position_display()
            
            self.log(f"[IK] ✓ Movement complete!")
            
            # Update stopper status after movement
            if 'movement_results' in result:
                for axis, move_result in result['movement_results'].items():
                    stopper_status = self.robot_controller.__dict__.get(f"{axis}_stopper_status", False)
                    self.update_stopper_indicator(axis, stopper_status)
        else:
            # Movement failed, but IK calculations are still valid
            # Update all displays to show the calculated values
            self.update_calculated_angles_display()
            self.update_sec_calculated_angles_display()
            self.update_movement_angles_display()
            self.update_last_position_display()
            
            self.log(f"[IK] ✗ {result['message']}")
        
        self.root.update()
    
    def on_go_to_zero(self):
        self.update_zeroised_indicator(False) # Reset zeroised indicator at start of action
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
            # Update last position display
            self.update_last_position_display()
            # Enable Move to Position button after successful zeroising
            self.move_to_position_button.config(state=tk.NORMAL)
            self.log("[System] Move to Position button ENABLED - robot zeroised ✓")
            # Enable PullUP button after successful zeroising
            self.pull_up_button.config(state=tk.NORMAL)
            self.log("[System] PullUP button ENABLED - robot zeroised ✓")
            # Enable Put Down button after successful zeroising
            self.put_down_button.config(state=tk.NORMAL)
            self.log("[System] Put Down button ENABLED - robot zeroised ✓")
        else:
            self.log("[Zero] ✗ Zeroising failed")
            # Keep Move to Position button disabled
            self.move_to_position_button.config(state=tk.DISABLED)
            # Keep PullUP button disabled
            self.pull_up_button.config(state=tk.DISABLED)
            # Keep Put Down button disabled
            self.put_down_button.config(state=tk.DISABLED)
        
        self.root.update()
    
    def on_pull_up(self):
        """Handle PullUP button press - execute pick and place sequence."""
        if not self.robot_controller.link:
            self.log("[PullUP] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[PullUP] Executing PullUP sequence...")
        self.root.update()
        
        # Call controller method
        success = self.robot_controller.pull_up()
        
        if success:
            self.log("[PullUP] ✓ PullUP sequence completed successfully")
        else:
            self.log("[PullUP] ✗ PullUP sequence failed")
        
        # Update stopper status after movement
        self.update_stopper_indicator('Y', self.robot_controller.Y_stopper_status)
        
        self.root.update()
    
    def on_put_down(self):
        """Handle Put Down button press - execute place sequence."""
        if not self.robot_controller.link:
            self.log("[PutDown] ERROR: Not connected to robot")
            self.root.update()
            return
        
        self.log("[PutDown] Executing Put Down sequence...")
        self.root.update()
        
        # Call controller method
        success = self.robot_controller.put_down()
        
        if success:
            self.log("[PutDown] ✓ Put Down sequence completed successfully")
        else:
            self.log("[PutDown] ✗ Put Down sequence failed")
        
        # Update stopper status after movement
        self.update_stopper_indicator('Y', self.robot_controller.Y_stopper_status)
        
        self.root.update()
    
    def on_pick_and_place_colors(self):
        """Pick one detected color item and place it onto another color position."""
        pick_color = self.pick_color_combo.get().strip()
        place_color = self.place_color_combo.get().strip()

        if not pick_color or not place_color:
            self.log("[PickPlace] ERROR: Please select both pick and target colors")
            return

        if pick_color == place_color:
            self.log("[PickPlace] ERROR: Pick and target colors must be different")
            return

        self.execute_pick_and_place_sequence(pick_color, place_color)

    def execute_pick_and_place_sequence(self, pick_color, place_color):
        """Execute pick/place sequence between two detected color targets."""
        seq_tag = f"[PickPlace {pick_color} -> {place_color}]"
        self.log(f"{seq_tag} Starting sequence...")
        self.root.update()

        # Enable Tech Mode for entire sequence to bypass Y stopper false triggers
        self.log(f"{seq_tag} Enabling Tech Mode (bypass stopper checks during sequence)")
        if not self.robot_controller.set_tech_mode(True):
            self.log(f"{seq_tag} WARNING: Failed to enable Tech Mode")

        pick_pos = self.get_item_position(pick_color)
        place_pos = self.get_item_position(place_color)

        if not pick_pos:
            self.log(f"{seq_tag} ERROR: {pick_color} item not detected")
            self.robot_controller.set_tech_mode(False)
            return

        if not place_pos:
            self.log(f"{seq_tag} ERROR: {place_color} item not detected")
            self.robot_controller.set_tech_mode(False)
            return

        pick_x, pick_y = pick_pos
        place_x, place_y = place_pos

        try:
            # Step 1: Move to picked color position
            self.log(f"{seq_tag} Step 1: Moving to {pick_color} position ({pick_x:.1f}, {pick_y:.1f})")
            self.root.update()
            move_result = self.robot_controller.move_to_position(pick_x, pick_y)
            if not move_result.get('success', False):
                self.log(f"{seq_tag} ERROR: Failed to move to {pick_color} position - {move_result.get('message', 'Unknown error')}")
                self.robot_controller.set_tech_mode(False)
                return

            # Step 2: Pull up
            self.log(f"{seq_tag} Step 2: Executing Pull Up")
            self.root.update()
            if not self.robot_controller.pull_up():
                self.log(f"{seq_tag} ERROR: Pull Up failed")
                self.robot_controller.set_tech_mode(False)
                return

            # Step 3: Move to place color position
            self.log(f"{seq_tag} Step 3: Moving to {place_color} position ({place_x:.1f}, {place_y:.1f})")
            self.root.update()
            move_result = self.robot_controller.move_to_position(place_x, place_y)
            if not move_result.get('success', False):
                self.log(f"{seq_tag} ERROR: Failed to move to {place_color} position - {move_result.get('message', 'Unknown error')}")
                self.robot_controller.set_tech_mode(False)
                return

            # Step 4: Put down
            self.log(f"{seq_tag} Step 4: Executing Put Down")
            self.root.update()
            if not self.robot_controller.put_down():
                self.log(f"{seq_tag} ERROR: Put Down failed")
                self.robot_controller.set_tech_mode(False)
                return

            # Step 5: Move to home position (32, 17)
            self.log(f"{seq_tag} Step 5: Moving to home position (32, 17)")
            self.root.update()
            move_result = self.robot_controller.move_to_position(32, 17)
            if not move_result.get('success', False):
                self.log(f"{seq_tag} ERROR: Failed to move to home position - {move_result.get('message', 'Unknown error')}")
                self.robot_controller.set_tech_mode(False)
                return

            self.log(f"{seq_tag} Sequence completed successfully!")

        except Exception as e:
            self.log(f"{seq_tag} ERROR: Exception during sequence - {str(e)}")
        finally:
            # Always disable Tech Mode at the end
            self.robot_controller.set_tech_mode(False)
            self.log(f"{seq_tag} Tech Mode disabled")
    
    def on_exit(self):
        """Handle Exit button press."""
        self.log("[System] Exit pressed - closing application")
        
        # Disable tech mode before exit for safety
        if self.tech_mode_enabled and self.robot_controller.link:
            self.log("[System] Disabling tech mode before exit...")
            self.robot_controller.set_tech_mode(False)
        
        # Cleanup camera
        if hasattr(self, 'camera_panel'):
            self.camera_panel.cleanup()
        
        self.robot_controller.cleanup()
        try:
            self.root.quit()
        finally:
            self.root.destroy()