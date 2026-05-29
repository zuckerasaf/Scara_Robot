"""
SCARA Robot Controller - Camera View Module

This module handles webcam capture using OpenCV and provides frames for display in the UI.
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
import json
import os
import math
from calibration import CalibrationClass
from TIcTacToe.board import update_cell_locations_from_calibration


class CameraCapture:
    """Handles webcam capture using OpenCV."""
    
    SETTINGS_FILE = "camera_settings.json"
    
    def __init__(self, camera_index=0, width=640, height=480):
        """
        Initialize camera capture.
        
        Args:
            camera_index: Index of the camera to use (default 0)
            width: Desired frame width
            height: Desired frame height
        """
        self.camera_index = camera_index
        self.width = width
        self.height = height
        self.cap = None
        self.is_running = False
        self.current_settings = {
            'brightness': 0,
            'contrast': 50,
            'saturation': 50,
            'exposure': -6
        }
        self.load_settings()
        
    def start(self):
        """Start camera capture."""
        try:
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                print(f"Error: Could not open camera {self.camera_index}")
                return False
            
            # Set camera properties
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            
            # Apply saved settings
            self.apply_settings()
            
            self.is_running = True
            print(f"Camera {self.camera_index} started successfully")
            print(f"Applied settings: Brightness={self.current_settings['brightness']}, "
                  f"Contrast={self.current_settings['contrast']}, "
                  f"Saturation={self.current_settings['saturation']}, "
                  f"Exposure={self.current_settings['exposure']}")
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
    def set_brightness(self, value):
        """Set camera brightness (usually 0-255 or -64 to 64, depends on camera)."""
        self.current_settings['brightness'] = value
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, value)
    
    def set_contrast(self, value):
        """Set camera contrast (usually 0-255 or 0-100, depends on camera)."""
        self.current_settings['contrast'] = value
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_CONTRAST, value)
    
    def set_saturation(self, value):
        """Set camera saturation (usually 0-255, depends on camera)."""
        self.current_settings['saturation'] = value
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_SATURATION, value)
    
    def set_exposure(self, value):
        """Set camera exposure (range depends on camera, often negative values for auto)."""
        self.current_settings['exposure'] = value
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_EXPOSURE, value)
    
    def set_gain(self, value):
        """Set camera gain (usually 0-100, depends on camera)."""
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_GAIN, value)
    
    def get_property(self, prop):
        """Get a camera property value."""
        if self.cap is not None and self.is_running:
            return self.cap.get(prop)
        return None
    
    def set_property(self, prop, value):
        """Set a camera property value."""
        if self.cap is not None and self.is_running:
            self.cap.set(prop, value)
    
    def apply_settings(self):
        """Apply current settings to the camera."""
        if self.cap is not None and self.is_running:
            self.cap.set(cv2.CAP_PROP_BRIGHTNESS, self.current_settings['brightness'])
            self.cap.set(cv2.CAP_PROP_CONTRAST, self.current_settings['contrast'])
            self.cap.set(cv2.CAP_PROP_SATURATION, self.current_settings['saturation'])
            self.cap.set(cv2.CAP_PROP_EXPOSURE, self.current_settings['exposure'])
    
    def save_settings(self):
        """Save current camera settings to file."""
        try:
            with open(self.SETTINGS_FILE, 'w') as f:
                json.dump(self.current_settings, f, indent=2)
            print(f"Camera settings saved to {self.SETTINGS_FILE}")
            return True
        except Exception as e:
            print(f"Error saving camera settings: {e}")
            return False
    
    def load_settings(self):
        """Load camera settings from file."""
        try:
            if os.path.exists(self.SETTINGS_FILE):
                with open(self.SETTINGS_FILE, 'r') as f:
                    loaded_settings = json.load(f)
                    self.current_settings.update(loaded_settings)
                print(f"Camera settings loaded from {self.SETTINGS_FILE}")
                return True
            else:
                print("No saved camera settings found, using defaults")
                return False
        except Exception as e:
            print(f"Error loading camera settings: {e}")
            return False
    
    def reset_to_defaults(self):
        """Reset settings to default values."""
        self.current_settings = {
            'brightness': 0,
            'contrast': 50,
            'saturation': 50,
            'exposure': -6
        }
        self.apply_settings()
    
    def stop(self):
        """Stop camera capture and release resources."""
        self.is_running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            print("Camera stopped")
    
    def get_frame(self):
        """
        Get a frame from the camera.
        
        Returns:
            numpy array: BGR frame from camera, or None if error
        """
        if not self.is_running or self.cap is None:
            return None
        
        ret, frame = self.cap.read()
        if ret:
            return frame
        else:
            return None
    
    def get_frame_rgb(self):
        """
        Get a frame from the camera in RGB format.
        
        Returns:
            numpy array: RGB frame from camera, or None if error
        """
        frame = self.get_frame()
        if frame is not None:
            # Convert BGR to RGB
            return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return None


class CameraPanel(tk.Frame):
    """Panel displaying camera feed."""
    
    def __init__(self, parent, camera_capture, update_interval=30, parent_app=None):
        """
        Initialize camera panel.
        
        Args:
            parent: Parent tkinter widget
            camera_capture: CameraCapture instance
            update_interval: Milliseconds between frame updates
            parent_app: Reference to parent application window for callbacks
        """
        super().__init__(parent, relief=tk.GROOVE, borderwidth=2, bg='#ffffff')
        
        self.camera_capture = camera_capture
        self.update_interval = update_interval
        self.is_active = False
        self.calibration = CalibrationClass()
        self.show_markers = False
        self.detection_in_progress = False
        self.detection_count = 0
        self.show_color_detection = False
        self.parent_app = parent_app
        self.frame_after_id = None
        self.is_closing = False
        self.last_tic_tac_toe_location_count = 0
        self.latest_marker_status_objects = None
        
        # Title
        title_frame = tk.Frame(self, bg='#ffffff')
        title_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        tk.Label(
            title_frame,
            text="Camera View",
            font=('Arial', 11, 'bold'),
            bg='#ffffff'
        ).pack(side=tk.LEFT)
        
        # Start/Stop button
        self.toggle_button = tk.Button(
            title_frame,
            text="Start Camera",
            command=self.toggle_camera,
            bg='#ccffcc',
            font=('Arial', 9)
        )
        self.toggle_button.pack(side=tk.RIGHT, padx=5)
        
        # Canvas for displaying camera feed
        self.canvas = tk.Canvas(
            self,
            width=640,
            height=480,
            bg='#000000',
            highlightthickness=1,
            highlightbackground='#888888'
        )
        self.canvas.pack(side=tk.TOP, padx=10, pady=10)
        
        # Info label
        self.info_label = tk.Label(
            self,
            text="Camera stopped - Click 'Start Camera' to begin",
            font=('Arial', 8, 'italic'),
            fg='#888888',
            bg='#ffffff'
        )
        self.info_label.pack(side=tk.TOP, pady=(0, 5))
        
        # Detect Marker button
        self.detect_button = tk.Button(
            self,
            text="Detect Markers",
            command=self.detect_markers,
            bg='#cce5ff',
            font=('Arial', 9),
            state=tk.DISABLED
        )
        self.detect_button.pack(side=tk.TOP, pady=(0, 5))

        # Clear marker display button (keeps calibration)
        self.clear_markers_button = tk.Button(
            self,
            text="Clear Marker Display",
            command=self.clear_marker_display,
            bg='#ffe6cc',
            font=('Arial', 9),
            state=tk.DISABLED
        )
        self.clear_markers_button.pack(side=tk.TOP, pady=(0, 5))
        
        # Color detection checkbox
        self.color_detect_var = tk.BooleanVar(value=False)
        self.color_detect_check = tk.Checkbutton(
            self,
            text="Detect Colored Objects (Green, Blue, Yellow, Red, Black, Pink, Brown)",
            variable=self.color_detect_var,
            command=self.toggle_color_detection,
            font=('Arial', 9),
            bg='#ffffff',
            state=tk.DISABLED
        )
        self.color_detect_check.pack(side=tk.TOP, pady=(0, 5))
        
        # Camera Settings Panel (collapsible)
        self.settings_frame = tk.Frame(
            self,
            relief=tk.RIDGE,
            borderwidth=2,
            bg='#f8f8f8'
        )
        self.settings_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        
        # Settings header with toggle button
        settings_header = tk.Frame(self.settings_frame, bg='#f8f8f8')
        settings_header.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.settings_visible = tk.BooleanVar(value=False)
        self.settings_toggle_btn = tk.Button(
            settings_header,
            text="▶ Camera Settings",
            command=self.toggle_settings,
            bg='#e0e0e0',
            font=('Arial', 9, 'bold'),
            relief=tk.FLAT,
            anchor='w'
        )
        self.settings_toggle_btn.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Settings content (initially hidden)
        self.settings_content = tk.Frame(self.settings_frame, bg='#f8f8f8')
        
        # Store slider references
        self.sliders = {}
        
        # Brightness slider
        self.sliders['brightness'] = self.create_slider(
            self.settings_content, "Brightness:", -64, 64, 
            self.camera_capture.current_settings['brightness'], 
            lambda v: self.camera_capture.set_brightness(int(float(v)))
        )
        
        # Contrast slider
        self.sliders['contrast'] = self.create_slider(
            self.settings_content, "Contrast:", 0, 100, 
            self.camera_capture.current_settings['contrast'], 
            lambda v: self.camera_capture.set_contrast(int(float(v)))
        )
        
        # Saturation slider
        self.sliders['saturation'] = self.create_slider(
            self.settings_content, "Saturation:", 0, 100, 
            self.camera_capture.current_settings['saturation'], 
            lambda v: self.camera_capture.set_saturation(int(float(v)))
        )
        
        # Exposure slider (note: -1 is often auto-exposure)
        self.sliders['exposure'] = self.create_slider(
            self.settings_content, "Exposure:", -13, 0, 
            self.camera_capture.current_settings['exposure'], 
            lambda v: self.camera_capture.set_exposure(int(float(v)))
        )
        
        # Buttons frame
        buttons_frame = tk.Frame(self.settings_content, bg='#f8f8f8')
        buttons_frame.pack(side=tk.TOP, pady=(5, 5))
        
        # Save as Default button
        save_btn = tk.Button(
            buttons_frame,
            text="Save as Default",
            command=self.save_camera_settings,
            bg='#ccffcc',
            font=('Arial', 8),
            width=15
        )
        save_btn.pack(side=tk.LEFT, padx=5)
        
        # Reset button
        reset_btn = tk.Button(
            buttons_frame,
            text="Reset to Defaults",
            command=self.reset_camera_settings,
            bg='#ffcccc',
            font=('Arial', 8),
            width=15
        )
        reset_btn.pack(side=tk.LEFT, padx=5)
        
        # Marker data table frame
        self.table_frame = tk.Frame(
            self,
            relief=tk.RIDGE,
            borderwidth=2,
            bg='#f0f0f0'
        )
        self.table_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        
        # Table title/status
        self.marker_status_label = tk.Label(
            self.table_frame,
            text="Detected markers: 0 | Calibration: Not calibrated",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0',
            fg='#555555'
        )
        self.marker_status_label.grid(row=0, column=0, columnspan=7, pady=5)
        
        # Table headers
        headers = ["ID", "Camera X", "Camera Y", "Marker 0 -> X", "Marker 0 -> Y", "Robot X", "Robot Y"]
        for col, header in enumerate(headers):
            tk.Label(
                self.table_frame,
                text=header,
                font=('Arial', 8, 'bold'),
                bg='#d0d0d0',
                relief=tk.RIDGE,
                width=10
            ).grid(row=1, column=col, padx=1, pady=1, sticky='ew')

        # Scrollable table body (show 6 rows, scroll for the rest)
        self.visible_table_rows = 6
        self.table_body_container = tk.Frame(self.table_frame, bg='#f0f0f0')
        self.table_body_container.grid(row=2, column=0, columnspan=7, sticky='ew')

        self.table_body_canvas = tk.Canvas(
            self.table_body_container,
            bg='#f0f0f0',
            highlightthickness=0,
            height=self.visible_table_rows * 24
        )
        self.table_body_scrollbar = tk.Scrollbar(
            self.table_body_container,
            orient='vertical',
            command=self.table_body_canvas.yview
        )
        self.table_body_canvas.configure(yscrollcommand=self.table_body_scrollbar.set)

        self.table_body_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.table_body_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.table_body_inner = tk.Frame(self.table_body_canvas, bg='#f0f0f0')
        self.table_body_window = self.table_body_canvas.create_window(
            (0, 0),
            window=self.table_body_inner,
            anchor='nw'
        )

        self.table_body_inner.bind(
            '<Configure>',
            lambda e: self.table_body_canvas.configure(scrollregion=self.table_body_canvas.bbox('all'))
        )
        self.table_body_canvas.bind(
            '<Configure>',
            lambda e: self.table_body_canvas.itemconfigure(self.table_body_window, width=e.width)
        )
        
        # Create label widgets for marker data (all configured markers, default to 36 rows).
        self.table_marker_ids = sorted(self.calibration.known_marker_positions.keys())
        if not self.table_marker_ids:
            self.table_marker_ids = list(range(36))

        self.marker_labels = {}
        for row_idx, marker_id in enumerate(self.table_marker_ids):
            self.marker_labels[marker_id] = {
                'id': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'cam_x': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'cam_y': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'marker0_x': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'marker0_y': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'rob_x': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'rob_y': tk.Label(self.table_body_inner, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10)
            }
            row = row_idx
            self.marker_labels[marker_id]['id'].grid(row=row, column=0, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['cam_x'].grid(row=row, column=1, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['cam_y'].grid(row=row, column=2, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['marker0_x'].grid(row=row, column=3, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['marker0_y'].grid(row=row, column=4, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['rob_x'].grid(row=row, column=5, padx=1, pady=1, sticky='ew')
            self.marker_labels[marker_id]['rob_y'].grid(row=row, column=6, padx=1, pady=1, sticky='ew')
        
        # Image reference (keep reference to prevent garbage collection)
        self.photo = None
    
    def update_marker_table(self):
        """Update the marker data table with current detections."""
        # Clear all rows first
        for marker_id in self.table_marker_ids:
            row = self.marker_labels[marker_id]
            row['id'].config(text=str(marker_id), bg='#ffffff')
            row['cam_x'].config(text="-", bg='#ffffff')
            row['cam_y'].config(text="-", bg='#ffffff')
            row['marker0_x'].config(text="-", bg='#ffffff')
            row['marker0_y'].config(text="-", bg='#ffffff')

            if marker_id in self.calibration.known_marker_positions:
                cfg_x = self.calibration.known_marker_positions[marker_id]['x']
                cfg_y = self.calibration.known_marker_positions[marker_id]['y']
                row['rob_x'].config(text=f"{cfg_x:.1f}", bg='#ffffff')
                row['rob_y'].config(text=f"{cfg_y:.1f}", bg='#ffffff')
            else:
                row['rob_x'].config(text="-", bg='#ffffff')
                row['rob_y'].config(text="-", bg='#ffffff')
        
        # Update camera values for detected markers
        if self.calibration.confirmed_markers:
            sorted_markers = sorted(self.calibration.confirmed_markers.keys())
            for marker_id in sorted_markers:
                if marker_id not in self.marker_labels:
                    continue
                    
                data = self.calibration.confirmed_markers[marker_id]
                if data['count'] > 0:
                    # Get camera coordinates
                    avg_corners = np.mean(data['corners'], axis=0)
                    center = avg_corners.mean(axis=0)
                    cam_x, cam_y = center
                    
                    # Determine row color
                    if marker_id in self.calibration.known_marker_positions:
                        bg_color = '#e6ffe6'  # Light green for configured calibration markers
                    else:
                        bg_color = '#ffffcc'  # Light yellow for others
                    
                    # Update marker ID and camera coords
                    self.marker_labels[marker_id]['id'].config(text=str(marker_id), bg=bg_color)
                    self.marker_labels[marker_id]['cam_x'].config(text=f"{cam_x:.1f}", bg=bg_color)
                    self.marker_labels[marker_id]['cam_y'].config(text=f"{cam_y:.1f}", bg=bg_color)

                    # Show configured marker coordinates in Marker 0 columns when available.
                    if marker_id in self.calibration.known_marker_positions:
                        cfg_x = self.calibration.known_marker_positions[marker_id]['x']
                        cfg_y = self.calibration.known_marker_positions[marker_id]['y']
                        self.marker_labels[marker_id]['marker0_x'].config(text=f"{cfg_x:.1f}", bg=bg_color)
                        self.marker_labels[marker_id]['marker0_y'].config(text=f"{cfg_y:.1f}", bg=bg_color)
                    elif self.calibration.is_calibrated:
                        # For unknown markers, show estimated marker frame coordinates if calibrated.
                        marker0_pos = self.calibration.camera_to_robot(cam_x, cam_y)
                        if marker0_pos is not None:
                            marker0_x, marker0_y = marker0_pos
                            self.marker_labels[marker_id]['marker0_x'].config(text=f"{marker0_x:.1f}", bg=bg_color)
                            self.marker_labels[marker_id]['marker0_y'].config(text=f"{marker0_y:.1f}", bg=bg_color)
                        else:
                            self.marker_labels[marker_id]['marker0_x'].config(text="N/A", bg=bg_color)
                            self.marker_labels[marker_id]['marker0_y'].config(text="N/A", bg=bg_color)
                    else:
                        self.marker_labels[marker_id]['marker0_x'].config(text="Not cal.", bg=bg_color)
                        self.marker_labels[marker_id]['marker0_y'].config(text="Not cal.", bg=bg_color)

                    # Keep Robot X/Y background in sync with row highlight.
                    self.marker_labels[marker_id]['rob_x'].config(bg=bg_color)
                    self.marker_labels[marker_id]['rob_y'].config(bg=bg_color)

        # Update status label with detection and calibration state.
        total_detected = len(self.calibration.confirmed_markers)
        configured_detected = sum(
            1 for marker_id in self.calibration.confirmed_markers
            if marker_id in self.calibration.known_marker_positions
        )

        if self.calibration.is_calibrated:
            calibration_text = "Calibrated"
            status_color = '#00aa00'
        elif self.detection_in_progress:
            calibration_text = f"Detecting ({self.detection_count}/10)"
            status_color = '#0066cc'
        else:
            calibration_text = "Not calibrated"
            status_color = '#555555'

        self.marker_status_label.config(
            text=(
                f"Detected markers: {total_detected} | "
                f"Configured detected: {configured_detected} | "
                f"Calibration: {calibration_text}"
            ),
            fg=status_color
        )
        
    def toggle_color_detection(self):
        """Toggle colored object detection on/off."""
        self.show_color_detection = self.color_detect_var.get()
        if self.show_color_detection:
            print("Color detection enabled")
        else:
            self.latest_marker_status_objects = None
            print("Color detection disabled")
    
    def toggle_camera(self):
        """Toggle camera on/off."""
        if self.is_active:
            self.stop_camera()
        else:
            self.start_camera()
    
    def start_camera(self):
        """Start the camera feed."""
        if self.camera_capture.start():
            self.is_active = True
            self.toggle_button.config(text="Stop Camera", bg='#ffcccc')
            self.detect_button.config(state=tk.NORMAL)
            self.clear_markers_button.config(state=tk.NORMAL)
            self.color_detect_check.config(state=tk.NORMAL)
            self.info_label.config(text="Camera active - Live feed")
            self.update_frame()
        else:
            self.info_label.config(
                text="Error: Could not start camera",
                fg='#ff0000'
            )
    
    def stop_camera(self):
        """Stop the camera feed."""
        # Cancel any queued frame callback first to avoid re-entry during shutdown.
        if self.frame_after_id is not None:
            try:
                self.after_cancel(self.frame_after_id)
            except Exception:
                pass
            self.frame_after_id = None

        self.is_active = False
        self.show_markers = False
        self.show_color_detection = False
        self.color_detect_var.set(False)
        self.camera_capture.stop()
        self.toggle_button.config(text="Start Camera", bg='#ccffcc')
        self.detect_button.config(state=tk.DISABLED)
        self.clear_markers_button.config(state=tk.DISABLED)
        self.color_detect_check.config(state=tk.DISABLED)
        self.info_label.config(
            text="Camera stopped - Click 'Start Camera' to begin",
            fg='#888888'
        )
        self.update_marker_table()
        
        # Clear canvas
        self.canvas.delete("all")
        self.canvas.create_text(
            320, 240,
            text="Camera Off",
            font=('Arial', 24),
            fill='#ffffff'
        )
    
    def detect_markers(self):
        """Trigger ArUco marker detection."""
        if not self.is_active:
            return

        # Start a fresh detection/calibration run
        self.show_markers = True
        self.detection_in_progress = True
        self.detection_count = 0
        self.calibration.reset_calibration()
        self.detect_button.config(text="Detecting...", bg='#ffffcc', state=tk.DISABLED)
        self.info_label.config(text="Running detection (0/10)...", fg='#0066cc')
        self.update_marker_table()

    def clear_marker_display(self):
        """Hide marker overlays on camera view without clearing detections/calibration."""
        self.show_markers = False
        self.detection_in_progress = False
        self.detection_count = 0

        self.detect_button.config(text="Detect Markers", bg='#cce5ff', state=tk.NORMAL if self.is_active else tk.DISABLED)
        if self.calibration.is_calibrated:
            self.info_label.config(text="Marker overlays hidden - calibration preserved", fg='#0066cc')
        else:
            self.info_label.config(text="Marker overlays hidden", fg='#0066cc')
        self.update_marker_table()

    def draw_dashed_polygon(self, frame, points, color=(0, 255, 255), thickness=2, dash_len=18, gap_len=12):
        """Draw a dashed closed polygon."""
        if points is None or len(points) < 2:
            return

        n = len(points)
        for i in range(n):
            p1 = points[i].astype(np.float32)
            p2 = points[(i + 1) % n].astype(np.float32)
            edge = p2 - p1
            dist = np.linalg.norm(edge)
            if dist <= 0:
                continue

            direction = edge / dist
            t = 0.0
            while t < dist:
                start = p1 + direction * t
                end = p1 + direction * min(t + dash_len, dist)
                cv2.line(
                    frame,
                    tuple(start.astype(int)),
                    tuple(end.astype(int)),
                    color,
                    thickness
                )
                t += dash_len + gap_len

    def refresh_tic_tac_toe_cell_locations(self):
        """Update Tic Tac Toe cells from the current detected marker positions."""
        if not self.calibration.is_calibrated:
            return

        updated_count = update_cell_locations_from_calibration(self.calibration)
        if updated_count != self.last_tic_tac_toe_location_count:
            self.last_tic_tac_toe_location_count = updated_count
            if self.parent_app and hasattr(self.parent_app, 'log'):
                self.parent_app.log(
                    f"[TicTacToe] Updated {updated_count}/9 cell locations from current markers"
                )

    def get_marker_robot_position(self, marker_number):
        """Return the current robot-coordinate center for a detected marker."""
        if not self.calibration.is_calibrated:
            return None

        data = self.calibration.confirmed_markers.get(marker_number)
        if not data or not data.get('corners'):
            return None

        avg_corners = np.mean(data['corners'], axis=0)
        center = avg_corners.mean(axis=0)
        marker_pos = self.calibration.camera_to_robot(center[0], center[1])
        if marker_pos is None:
            return None

        return (float(marker_pos[0]), float(marker_pos[1]))

    def marker_status(self, marker_number, max_distance_cm=3.0):
        """Return empty, green, red, or unknown for a marker's current cell status."""
        marker_pos = self.get_marker_robot_position(marker_number)
        if marker_pos is None or self.latest_marker_status_objects is None:
            return "unknown"

        marker_x, marker_y = marker_pos
        nearest_status = None
        nearest_distance = None

        for color in ("green", "red"):
            for object_x, object_y in self.latest_marker_status_objects.get(color, []):
                distance = math.hypot(object_x - marker_x, object_y - marker_y)
                if nearest_distance is None or distance < nearest_distance:
                    nearest_distance = distance
                    nearest_status = color

        if nearest_distance is not None and nearest_distance <= max_distance_cm:
            return nearest_status

        return "empty"
    
    def update_frame(self):
        """Update the camera frame on the canvas."""
        if not self.is_active or self.is_closing:
            return
        
        # Get frame from camera (BGR format)
        frame_bgr = self.camera_capture.get_frame()
        
        if frame_bgr is not None:
            # Apply marker detection if enabled
            if self.show_markers:
                # Run detection multiple times
                if self.detection_in_progress and self.detection_count < 10:
                    frame_bgr, markers = self.calibration.detect_markers(frame_bgr)
                    self.detection_count += 1
                    self.info_label.config(
                        text=f"Running detection ({self.detection_count}/10)...",
                        fg='#0066cc'
                    )
                    
                    # After 10 attempts, finalize
                    if self.detection_count >= 10:
                        self.detection_in_progress = False
                        self.detect_button.config(text="Detect Markers", bg='#cce5ff', state=tk.NORMAL)
                        if self.calibration.confirmed_markers:
                            marker_ids = list(self.calibration.confirmed_markers.keys())
                            print(f"\n{'='*60}")
                            print(f"Detection complete: Found markers {marker_ids}")
                            print(f"{'='*60}")
                            
                            # Print detected marker positions (camera and configured robot coords)
                            for marker_id in sorted(self.calibration.confirmed_markers.keys()):
                                data = self.calibration.confirmed_markers[marker_id]
                                if data['count'] > 0:
                                    avg_corners = np.mean(data['corners'], axis=0)
                                    center = avg_corners.mean(axis=0)
                                    
                                    # Get configured robot position if it exists
                                    if marker_id in self.calibration.known_marker_positions:
                                        config_x = self.calibration.known_marker_positions[marker_id]['x']
                                        config_y = self.calibration.known_marker_positions[marker_id]['y']
                                        print(f"Marker {marker_id}: Camera({center[0]:.1f}, {center[1]:.1f}) px | Config Robot({config_x}, {config_y}) cm")
                                    else:
                                        print(f"Marker {marker_id}: Camera({center[0]:.1f}, {center[1]:.1f}) px | No config position")
                            print(f"{'='*60}\n")
                            
                            # Use all configured marker IDs as calibration markers (minimum 4 required).
                            calibration_markers_found = [
                                m for m in marker_ids if m in self.calibration.known_marker_positions
                            ]
                            if len(calibration_markers_found) >= 4:
                                if self.calibration.compute_calibration():
                                    self.refresh_tic_tac_toe_cell_locations()
                                    self.info_label.config(
                                        text=(
                                            f"✓ Calibrated with {len(calibration_markers_found)} configured markers! "
                                            f"Total detected: {marker_ids}"
                                        ),
                                        fg='#00aa00'
                                    )
                                    self.update_marker_table()
                                else:
                                    self.info_label.config(
                                        text=f"Calibration failed. Detected: {marker_ids}",
                                        fg='#ff6600'
                                    )
                                    self.update_marker_table()
                            else:
                                self.info_label.config(
                                    text=(
                                        f"Detected {len(marker_ids)} marker(s): {marker_ids} "
                                        f"(need at least 4 configured markers for calibration)"
                                    ),
                                    fg='#0066cc'
                                )
                                self.update_marker_table()
                        else:
                            self.info_label.config(
                                text="No markers detected after 10 attempts",
                                fg='#ff6600'
                            )
                else:
                    # Keep showing the detected markers
                    frame_bgr, markers = self.calibration.detect_markers(frame_bgr)
                    self.refresh_tic_tac_toe_cell_locations()
                    
                    # Update the marker table with all detected markers
                    self.update_marker_table()

            # Keep marker tracking updated in background for ROI polygon even when overlays are hidden.
            if self.show_color_detection and not self.show_markers:
                _, _ = self.calibration.detect_markers(frame_bgr, draw=False)
                self.refresh_tic_tac_toe_cell_locations()
            
            # Apply color detection if enabled
            if self.show_color_detection:
                # Detect colored objects using fixed ROI
                detected_colors = self.calibration.detect_colored_objects(frame_bgr, use_roi=True)
                frame_bgr = self.calibration.draw_colored_objects(frame_bgr, detected_colors)
                
                # Draw fixed ROI boundary for reference
                marker_roi_polygon = self.calibration.get_marker_roi_polygon(frame_bgr.shape)
                if marker_roi_polygon is not None:
                    self.draw_dashed_polygon(frame_bgr, marker_roi_polygon, color=(0, 255, 255), thickness=3)
                
                transformed_objects = {}
                marker_status_objects = {"green": [], "red": []}

                for color in ['green', 'yellow', 'blue', 'red', 'black', 'pink', 'brown']:
                    if color in detected_colors and detected_colors[color]:
                        transformed_objects[color] = []

                        for (x, y, w, h, area) in detected_colors[color]:
                            # Get center of bounding box
                            center_x = x + w // 2
                            center_y = y + h // 2

                            # Transform camera coords to Marker 0 coords
                            if self.calibration.is_calibrated:
                                marker0_pos = self.calibration.camera_to_robot(center_x, center_y)
                                if marker0_pos is not None:
                                    marker0_x, marker0_y = marker0_pos

                                    # Robot coordinates must match marker0 coordinates exactly.
                                    robot_x = marker0_x
                                    robot_y = marker0_y

                                    # Store: (camera_x, camera_y, marker0_x, marker0_y, robot_x, robot_y)
                                    transformed_objects[color].append(
                                        (center_x, center_y, marker0_x, marker0_y, robot_x, robot_y)
                                    )
                                    if color in marker_status_objects:
                                        marker_status_objects[color].append((float(robot_x), float(robot_y)))

                if self.calibration.is_calibrated:
                    self.latest_marker_status_objects = marker_status_objects
                else:
                    self.latest_marker_status_objects = None

                # Transform detected objects to robot coordinates and update item table
                if self.parent_app and hasattr(self.parent_app, 'update_item_table'):
                    # Update the item table in the main app
                    self.parent_app.update_item_table(transformed_objects)
                
            
            # Convert to RGB for display
            frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        else:
            frame = None
        
        if frame is not None:
            # Resize frame to fit canvas if needed
            h, w = frame.shape[:2]
            canvas_w = self.canvas.winfo_width()
            canvas_h = self.canvas.winfo_height()
            
            # Use default size if canvas not yet rendered
            if canvas_w <= 1:
                canvas_w = 640
            if canvas_h <= 1:
                canvas_h = 480
            
            # Resize frame to fit canvas while maintaining aspect ratio
            scale = min(canvas_w / w, canvas_h / h)
            new_w = int(w * scale)
            new_h = int(h * scale)
            
            if scale != 1:
                frame = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
            
            # Convert to PIL Image
            img = Image.fromarray(frame)
            
            # Convert to PhotoImage
            self.photo = ImageTk.PhotoImage(image=img)
            
            # Update canvas
            self.canvas.delete("all")
            self.canvas.create_image(
                canvas_w // 2,
                canvas_h // 2,
                image=self.photo,
                anchor=tk.CENTER
            )
        else:
            # Display error message
            self.canvas.delete("all")
            self.canvas.create_text(
                320, 240,
                text="No Frame",
                font=('Arial', 16),
                fill='#ff0000'
            )
        
        # Schedule next update
        if self.is_active:
            self.frame_after_id = self.after(self.update_interval, self.update_frame)
    
    def create_slider(self, parent, label_text, from_val, to_val, default_val, command):
        """Create a labeled slider control."""
        frame = tk.Frame(parent, bg='#f8f8f8')
        frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=2)
        
        label = tk.Label(
            frame,
            text=label_text,
            font=('Arial', 8),
            bg='#f8f8f8',
            width=12,
            anchor='w'
        )
        label.pack(side=tk.LEFT, padx=(0, 5))
        
        slider = tk.Scale(
            frame,
            from_=from_val,
            to=to_val,
            orient=tk.HORIZONTAL,
            command=command,
            bg='#f8f8f8',
            font=('Arial', 7),
            length=200,
            showvalue=True
        )
        slider.set(default_val)
        slider.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        return slider
    
    def toggle_settings(self):
        """Toggle visibility of camera settings panel."""
        if self.settings_visible.get():
            # Hide settings
            self.settings_content.pack_forget()
            self.settings_toggle_btn.config(text="▶ Camera Settings")
            self.settings_visible.set(False)
        else:
            # Show settings
            self.settings_content.pack(side=tk.TOP, fill=tk.X, padx=5, pady=(0, 5))
            self.settings_toggle_btn.config(text="▼ Camera Settings")
            self.settings_visible.set(True)
    
    def reset_camera_settings(self):
        """Reset camera settings to default values."""
        # Reset to factory defaults
        self.camera_capture.reset_to_defaults()
        
        # Update slider positions
        self.sliders['brightness'].set(0)
        self.sliders['contrast'].set(50)
        self.sliders['saturation'].set(50)
        self.sliders['exposure'].set(-6)
        
        print("Camera settings reset to factory defaults")
    
    def save_camera_settings(self):
        """Save current camera settings as defaults."""
        if self.camera_capture.save_settings():
            print(f"✓ Saved: Brightness={self.camera_capture.current_settings['brightness']}, "
                  f"Contrast={self.camera_capture.current_settings['contrast']}, "
                  f"Saturation={self.camera_capture.current_settings['saturation']}, "
                  f"Exposure={self.camera_capture.current_settings['exposure']}")
            
            # Show confirmation to user
            if hasattr(self, 'info_label'):
                original_text = self.info_label.cget('text')
                original_fg = self.info_label.cget('fg')
                self.info_label.config(text="✓ Camera settings saved as default!", fg='#00aa00')
                self.after(2000, lambda: self.info_label.config(text=original_text, fg=original_fg))
        else:
            print("✗ Failed to save camera settings")
    
    def cleanup(self):
        """Cleanup resources when closing."""
        self.is_closing = True
        self.stop_camera()
