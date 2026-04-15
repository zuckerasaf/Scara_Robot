"""
SCARA Robot Controller - Camera View Module

This module handles webcam capture using OpenCV and provides frames for display in the UI.
"""

import cv2
import numpy as np
from PIL import Image, ImageTk
import tkinter as tk
from calibration import CalibrationClass


class CameraCapture:
    """Handles webcam capture using OpenCV."""
    
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
            
            self.is_running = True
            print(f"Camera {self.camera_index} started successfully")
            return True
        except Exception as e:
            print(f"Error starting camera: {e}")
            return False
    
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
        
        # Color detection checkbox
        self.color_detect_var = tk.BooleanVar(value=False)
        self.color_detect_check = tk.Checkbutton(
            self,
            text="Detect Colored Objects (Red, Blue, Yellow)",
            variable=self.color_detect_var,
            command=self.toggle_color_detection,
            font=('Arial', 9),
            bg='#ffffff',
            state=tk.DISABLED
        )
        self.color_detect_check.pack(side=tk.TOP, pady=(0, 5))
        
        # Marker data table frame
        self.table_frame = tk.Frame(
            self,
            relief=tk.RIDGE,
            borderwidth=2,
            bg='#f0f0f0'
        )
        self.table_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=(0, 10))
        
        # Table title
        tk.Label(
            self.table_frame,
            text="Detected Markers",
            font=('Arial', 10, 'bold'),
            bg='#f0f0f0'
        ).grid(row=0, column=0, columnspan=7, pady=5)
        
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
        
        # Create label widgets for marker data (up to 6 markers: 0-5)
        self.marker_labels = {}
        for i in range(6):
            self.marker_labels[i] = {
                'id': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'cam_x': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'cam_y': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'marker0_x': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'marker0_y': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'rob_x': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10),
                'rob_y': tk.Label(self.table_frame, text="-", font=('Arial', 8), bg='#ffffff', relief=tk.RIDGE, width=10)
            }
            row = i + 2
            self.marker_labels[i]['id'].grid(row=row, column=0, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['cam_x'].grid(row=row, column=1, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['cam_y'].grid(row=row, column=2, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['marker0_x'].grid(row=row, column=3, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['marker0_y'].grid(row=row, column=4, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['rob_x'].grid(row=row, column=5, padx=1, pady=1, sticky='ew')
            self.marker_labels[i]['rob_y'].grid(row=row, column=6, padx=1, pady=1, sticky='ew')
        
        # Image reference (keep reference to prevent garbage collection)
        self.photo = None
    
    def update_marker_table(self):
        """Update the marker data table with current detections."""
        # Clear all rows first
        for i in range(6):
            self.marker_labels[i]['id'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['cam_x'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['cam_y'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['marker0_x'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['marker0_y'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['rob_x'].config(text="-", bg='#ffffff')
            self.marker_labels[i]['rob_y'].config(text="-", bg='#ffffff')
        
        # Update with detected markers
        if self.calibration.confirmed_markers:
            sorted_markers = sorted(self.calibration.confirmed_markers.keys())
            for idx, marker_id in enumerate(sorted_markers):
                if idx >= 6:  # Only show up to 6 markers
                    break
                    
                data = self.calibration.confirmed_markers[marker_id]
                if data['count'] > 0:
                    # Get camera coordinates
                    avg_corners = np.mean(data['corners'], axis=0)
                    center = avg_corners.mean(axis=0)
                    cam_x, cam_y = center
                    
                    # Determine row color
                    if marker_id == 5:
                        bg_color = '#e6f2ff'  # Light blue for marker 5
                    elif marker_id in [0, 1, 2, 3]:
                        bg_color = '#e6ffe6'  # Light green for calibration markers
                    else:
                        bg_color = '#ffffcc'  # Light yellow for others
                    
                    # Update marker ID and camera coords
                    self.marker_labels[idx]['id'].config(text=str(marker_id), bg=bg_color)
                    self.marker_labels[idx]['cam_x'].config(text=f"{cam_x:.1f}", bg=bg_color)
                    self.marker_labels[idx]['cam_y'].config(text=f"{cam_y:.1f}", bg=bg_color)
                    
                    # Get Marker 0 relative coordinates and Robot coordinates
                    marker0_x = None
                    marker0_y = None
                    
                    # For reference markers (0-3): Use configured static positions
                    # For other markers: Calculate position from calibration
                    if marker_id in [0, 1, 2, 3] and marker_id in self.calibration.known_marker_positions:
                        # Show configured reference position (relative to Marker 0)
                        marker0_x = self.calibration.known_marker_positions[marker_id]['x']
                        marker0_y = self.calibration.known_marker_positions[marker_id]['y']
                        self.marker_labels[idx]['marker0_x'].config(text=f"{marker0_x:.1f}", bg=bg_color)
                        self.marker_labels[idx]['marker0_y'].config(text=f"{marker0_y:.1f}", bg=bg_color)
                    elif self.calibration.is_calibrated:
                        # Calculate position for non-reference markers
                        marker0_pos = self.calibration.camera_to_robot(cam_x, cam_y)
                        if marker0_pos is not None:
                            marker0_x, marker0_y = marker0_pos
                            self.marker_labels[idx]['marker0_x'].config(text=f"{marker0_x:.1f}", bg=bg_color)
                            self.marker_labels[idx]['marker0_y'].config(text=f"{marker0_y:.1f}", bg=bg_color)
                        else:
                            self.marker_labels[idx]['marker0_x'].config(text="N/A", bg=bg_color)
                            self.marker_labels[idx]['marker0_y'].config(text="N/A", bg=bg_color)
                    else:
                        self.marker_labels[idx]['marker0_x'].config(text="Not cal.", bg=bg_color)
                        self.marker_labels[idx]['marker0_y'].config(text="Not cal.", bg=bg_color)
                    
                    # Apply custom transformation: Marker 0 coordinates -> Robot coordinates
                    if marker0_x is not None and marker0_y is not None:
                        # Robot Y = Marker 0 -> Y + 15
                        robot_y = marker0_y + 15
                        
                        # Robot X formula
                        if marker0_x <= 25:
                            robot_x = (marker0_x - 25) * -1
                        else:
                            robot_x = marker0_x * -1 + 25
                        
                        self.marker_labels[idx]['rob_x'].config(text=f"{robot_x:.1f}", bg=bg_color)
                        self.marker_labels[idx]['rob_y'].config(text=f"{robot_y:.1f}", bg=bg_color)
                    else:
                        self.marker_labels[idx]['rob_x'].config(text="-", bg=bg_color)
                        self.marker_labels[idx]['rob_y'].config(text="-", bg=bg_color)
        
    def toggle_color_detection(self):
        """Toggle colored object detection on/off."""
        self.show_color_detection = self.color_detect_var.get()
        if self.show_color_detection:
            print("Color detection enabled")
        else:
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
        self.is_active = False
        self.show_markers = False
        self.show_color_detection = False
        self.color_detect_var.set(False)
        self.camera_capture.stop()
        self.toggle_button.config(text="Start Camera", bg='#ccffcc')
        self.detect_button.config(state=tk.DISABLED)
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
            
        if not self.show_markers:
            # Start detection
            self.show_markers = True
            self.detection_in_progress = True
            self.detection_count = 0
            self.calibration.reset_calibration()
            self.detect_button.config(text="Detecting...", bg='#ffffcc', state=tk.DISABLED)
            self.info_label.config(text="Running detection (0/10)...", fg='#0066cc')
            self.update_marker_table()
        else:
            # Stop detection
            self.show_markers = False
            self.detection_in_progress = False
            self.detection_count = 0
            self.calibration.reset_calibration()
            self.detect_button.config(text="Detect Markers", bg='#cce5ff', state=tk.NORMAL)
            self.info_label.config(text="Camera active - Live feed", fg='#888888')
            self.update_marker_table()
    
    def update_frame(self):
        """Update the camera frame on the canvas."""
        if not self.is_active:
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
                        self.detect_button.config(text="Clear Markers", bg='#ffcccc', state=tk.NORMAL)
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
                            
                            # Check if we have at least 3 calibration markers (0-3) and compute calibration
                            calibration_markers_found = [m for m in [0, 1, 2, 3] if m in marker_ids]
                            if len(calibration_markers_found) >= 3:
                                if self.calibration.compute_calibration():
                                    self.info_label.config(
                                        text=f"✓ Calibrated with {len(calibration_markers_found)} markers! Total detected: {marker_ids}",
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
                                    text=f"Detected {len(marker_ids)} marker(s): {marker_ids} (need 3+ from [0,1,2,3] for calibration)",
                                    fg='#0066cc'
                                )
                                self.update_marker_table()
                        else:
                            self.info_label.config(
                                text="No markers detected after 10 attempts",
                                fg='#ff6600'
                            )
                else:
                    # Keep showing the detected markers and update if marker 5 is found
                    frame_bgr, markers = self.calibration.detect_markers(frame_bgr)
                    
                    # If marker 5 is detected and we're calibrated, calculate its position
                    if self.calibration.is_calibrated and 5 in self.calibration.confirmed_markers:
                        marker_5_data = self.calibration.confirmed_markers[5]
                        if marker_5_data['count'] > 0:
                            # Get average center position of marker 5
                            avg_corners = np.mean(marker_5_data['corners'], axis=0)
                            center = avg_corners.mean(axis=0)
                            
                            # Transform to Marker 0 relative coordinates
                            marker0_pos = self.calibration.camera_to_robot(center[0], center[1])
                            if marker0_pos is not None:
                                marker0_x, marker0_y = marker0_pos
                                
                                # Apply custom transformation: Marker 0 -> Robot coordinates
                                # Robot Y = Marker 0 -> Y + 15
                                robot_y = marker0_y + 15
                                
                                # Robot X formula
                                if marker0_x <= 25:
                                    robot_x = (marker0_x - 25) * -1
                                else:
                                    robot_x = marker0_x * -1 + 25
                                
                                self.calibration.marker_5_robot_position = (robot_x, robot_y)
                                print(f"Marker 5: Camera({center[0]:.1f}, {center[1]:.1f}) -> Marker0({marker0_x:.2f}, {marker0_y:.2f}) -> Robot({robot_x:.2f}, {robot_y:.2f}) cm")
                                self.info_label.config(
                                    text=f"✓ Marker 5 at Robot({robot_x:.1f}, {robot_y:.1f}) cm",
                                    fg='#0000ff'
                                )
                    
                    # Update the marker table with all detected markers
                    self.update_marker_table()
            
            # Apply color detection if enabled
            if self.show_color_detection:
                # Detect colored objects using fixed ROI
                detected_colors = self.calibration.detect_colored_objects(frame_bgr, use_roi=True)
                frame_bgr = self.calibration.draw_colored_objects(frame_bgr, detected_colors)
                
                # Draw fixed ROI boundary for reference
                if self.calibration.detection_roi is not None:
                    x, y, w, h = self.calibration.detection_roi
                    cv2.rectangle(frame_bgr, (x, y), (x + w, y + h), (0, 255, 255), 2)  # Yellow boundary
                
                # Transform detected objects to robot coordinates and update item table
                if self.parent_app and hasattr(self.parent_app, 'update_item_table'):
                    transformed_objects = {}
                    
                    for color in ['red', 'yellow', 'blue']:
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
                                        
                                        # Apply custom transformation: Marker 0 -> Robot coordinates
                                        # Robot Y = Marker 0 -> Y + 15
                                        robot_y = marker0_y + 15
                                        
                                        # Robot X formula
                                        if marker0_x <= 25:
                                            robot_x = (marker0_x - 25) * -1
                                        else:
                                            robot_x = marker0_x * -1 + 25
                                        
                                        # Store: (camera_x, camera_y, marker0_x, marker0_y, robot_x, robot_y)
                                        transformed_objects[color].append(
                                            (center_x, center_y, marker0_x, marker0_y, robot_x, robot_y)
                                        )
                    
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
            self.after(self.update_interval, self.update_frame)
    
    def cleanup(self):
        """Cleanup resources when closing."""
        self.stop_camera()
