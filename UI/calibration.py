"""
SCARA Robot Controller - Calibration Module

This module handles ArUco marker detection and camera-to-robot coordinate transformation.
"""

import cv2
import numpy as np
import json
import os


class CalibrationClass:
    """Handles ArUco marker detection for robot calibration."""
    
    def __init__(self):
        """Initialize calibration with ArUco detector."""
        self.aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)
        self.aruco_params = cv2.aruco.DetectorParameters()
        self.detector = cv2.aruco.ArucoDetector(self.aruco_dict, self.aruco_params)
        self.detected_markers = []
        self.confirmed_markers = {}  # Store confirmed marker positions
        self.detection_count = 0
        self.detection_attempts = 10
        self.known_marker_positions = self.load_marker_positions()
        self.calibration_matrix = None
        self.is_calibrated = False
        self.marker_5_robot_position = None
        
        # Fixed ROI for color detection (x, y, width, height) in pixels
        # Adjust these values to match your workspace area
        self.detection_roi = (50, 50, 540, 380)  # Default: 50px margin from 640x480 camera
    
    def load_marker_positions(self):
        """Load known marker positions from axis_config.json"""
        try:
            config_path = os.path.join(os.path.dirname(__file__), 'axis_config.json')
            with open(config_path, 'r') as f:
                config = json.load(f)
                
                # Load marker positions
                markers = config.get('calibration_markers', {})
                positions = {}
                for key, value in markers.items():
                    if key.startswith('marker_') and 'id' in value:
                        marker_id = value['id']
                        positions[marker_id] = {
                            'x': value['x_cm'],
                            'y': value['y_cm']
                        }
                print(f"Loaded {len(positions)} marker positions from config")
                
                # Load detection ROI if available
                detection_settings = config.get('detection_settings', {})
                if 'color_detection_roi' in detection_settings:
                    roi = detection_settings['color_detection_roi']
                    self.detection_roi = (roi.get('x', 50), roi.get('y', 50), 
                                         roi.get('width', 540), roi.get('height', 380))
                    print(f"Loaded detection ROI: {self.detection_roi}")
                
                return positions
        except Exception as e:
            print(f"Error loading marker positions: {e}")
            return {}
    
    def compute_calibration(self):
        """Compute camera-to-robot transformation using detected markers 0-3 (minimum 3 required)."""
        # Check if we have at least 3 calibration markers
        calibration_markers = [0, 1, 2, 3]
        detected_ids = list(self.confirmed_markers.keys())
        
        # Count how many calibration markers are detected
        detected_calibration_markers = [m for m in calibration_markers if m in detected_ids]
        
        if len(detected_calibration_markers) < 3:
            missing = [m for m in calibration_markers if m not in detected_ids]
            print(f"Cannot calibrate: Need at least 3 markers, found {len(detected_calibration_markers)}. Missing: {missing}")
            return False
        
        # Build point correspondences using detected calibration markers
        camera_points = []
        robot_points = []
        used_markers = []
        
        for marker_id in detected_calibration_markers:
            if marker_id in self.known_marker_positions:
                # Robot coordinates (from config)
                robot_x = self.known_marker_positions[marker_id]['x']
                robot_y = self.known_marker_positions[marker_id]['y']
                robot_points.append([robot_x, robot_y])
                
                # Camera coordinates (averaged from detections)
                avg_corners = np.mean(self.confirmed_markers[marker_id]['corners'], axis=0)
                center = avg_corners.mean(axis=0)
                camera_points.append(center)
                used_markers.append(marker_id)
                
                print(f"  Marker {marker_id}: Camera({center[0]:.1f}, {center[1]:.1f}) -> Robot({robot_x}, {robot_y})")
        
        if len(robot_points) < 3:
            print("Not enough markers with known positions")
            return False
        
        # Convert to numpy arrays
        camera_points = np.array(camera_points, dtype=np.float32)
        robot_points = np.array(robot_points, dtype=np.float32)
        
        # Calculate affine transformation from camera to robot
        self.calibration_matrix, _ = cv2.estimateAffinePartial2D(camera_points, robot_points)
        
        if self.calibration_matrix is not None:
            self.is_calibrated = True
            print(f"✓ Calibration successful using {len(robot_points)} markers: {used_markers}")
            print(f"Transformation matrix:\n{self.calibration_matrix}")
            print(f"  Translation: ({self.calibration_matrix[0,2]:.2f}, {self.calibration_matrix[1,2]:.2f})")
            print(f"  Scale/Rotation: [{self.calibration_matrix[0,0]:.4f}, {self.calibration_matrix[0,1]:.4f}]")
            print(f"                  [{self.calibration_matrix[1,0]:.4f}, {self.calibration_matrix[1,1]:.4f}]")
            
            # Show where origin (0,0) is in camera coordinates
            origin_cam = self.robot_to_camera(0, 0)
            if origin_cam is not None:
                print(f"  Origin (0,0) in camera: ({origin_cam[0]:.1f}, {origin_cam[1]:.1f}) pixels")
            
            return True
        else:
            print("✗ Calibration failed")
            return False
    
    def camera_to_robot(self, camera_x, camera_y):
        """Transform camera pixel coordinates to robot coordinates (cm)."""
        if not self.is_calibrated or self.calibration_matrix is None:
            return None
        
        # Apply affine transformation
        point = np.array([[[camera_x, camera_y]]], dtype=np.float32)
        transformed = cv2.transform(point, self.calibration_matrix)
        return transformed[0][0]
    
    def robot_to_camera(self, robot_x, robot_y):
        """Transform robot coordinates (cm) to camera pixel coordinates."""
        if not self.is_calibrated or self.calibration_matrix is None:
            return None
        
        # Invert the affine transformation matrix
        try:
            # For affine transform [a b c; d e f], we need to invert it
            A = self.calibration_matrix[:, :2]
            b = self.calibration_matrix[:, 2]
            A_inv = np.linalg.inv(A)
            
            # Apply inverse transformation
            point = np.array([robot_x, robot_y])
            camera_point = A_inv @ (point - b)
            return camera_point
        except Exception as e:
            print(f"Error inverting transformation: {e}")
            return None
        
    def detect_markers(self, frame):
        """
        Detect ArUco markers in the given frame.
        
        Args:
            frame: BGR image from camera
            
        Returns:
            tuple: (annotated_frame, detected_markers_info)
                - annotated_frame: Frame with markers outlined
                - detected_markers_info: List of detected marker IDs and corners
        """
        if frame is None:
            return None, []
        
        # Convert to grayscale for detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect markers using new API
        corners, ids, rejected = self.detector.detectMarkers(gray)
        
        # Create a copy of the frame to draw on
        annotated_frame = frame.copy()
        
        # Store detected marker info for this frame
        if ids is not None and len(ids) > 0:
            for i, marker_id in enumerate(ids):
                marker_corners = corners[i][0]
                marker_id_int = int(marker_id[0])
                
                # Add to confirmed markers (accumulate detections)
                if marker_id_int not in self.confirmed_markers:
                    self.confirmed_markers[marker_id_int] = {
                        'corners': [],
                        'count': 0
                    }
                
                self.confirmed_markers[marker_id_int]['corners'].append(marker_corners)
                self.confirmed_markers[marker_id_int]['count'] += 1
        
        # Draw confirmed markers on the frame
        if self.confirmed_markers:
            for marker_id, data in self.confirmed_markers.items():
                if data['count'] > 0:
                    # Average the corner positions
                    avg_corners = np.mean(data['corners'], axis=0).astype(np.int32)
                    
                    # Determine color: green for calibration markers (0-3), blue for marker 5
                    if marker_id in [0, 1, 2, 3]:
                        color = (0, 255, 0)  # Green
                        label = f"ID: {marker_id}"
                    elif marker_id == 5:
                        color = (255, 0, 0)  # Blue
                        if self.marker_5_robot_position is not None:
                            x, y = self.marker_5_robot_position
                            label = f"ID: 5 ({x:.1f}, {y:.1f})cm"
                        else:
                            label = f"ID: 5"
                    else:
                        color = (0, 255, 255)  # Yellow for unknown
                        label = f"ID: {marker_id}"
                    
                    # Draw the square
                    cv2.polylines(annotated_frame, [avg_corners], True, color, 3)
                    
                    # Draw the ID/position
                    center = avg_corners.mean(axis=0).astype(int)
                    cv2.putText(
                        annotated_frame,
                        label,
                        tuple(center - [40, 20]),
                        cv2.FONT_HERSHEY_SIMPLEX,
                        0.6,
                        color,
                        2
                    )
        
        # Draw origin point (0,0) at Marker 0 position if detected
        if 0 in self.confirmed_markers and self.confirmed_markers[0]['count'] > 0:
            # Get marker 0 center position
            avg_corners = np.mean(self.confirmed_markers[0]['corners'], axis=0)
            origin_pos = avg_corners.mean(axis=0).astype(int)
            ox, oy = origin_pos
            
            # Draw crosshair at origin (marker 0)
            cv2.drawMarker(
                annotated_frame,
                (ox, oy),
                (0, 0, 255),  # Red
                cv2.MARKER_CROSS,
                30,
                3
            )
            # Draw circle around it
            cv2.circle(annotated_frame, (ox, oy), 15, (0, 0, 255), 3)
            # Label it
            cv2.putText(
                annotated_frame,
                "Origin (0,0)",
                (ox + 20, oy - 20),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )
        
        return annotated_frame, list(self.confirmed_markers.keys())
    
    def detect_workspace_boundary(self, frame):
        """
        Detect the workspace boundary (large red rectangle/mat).
        
        Args:
            frame: BGR image from camera
            
        Returns:
            tuple: (x, y, w, h) of workspace boundary, or None if not found
        """
        if frame is None:
            return None
        
        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Detect red (mat boundary)
        lower_red1 = np.array([0, 100, 100])
        upper_red1 = np.array([10, 255, 255])
        lower_red2 = np.array([160, 100, 100])
        upper_red2 = np.array([180, 255, 255])
        
        mask1 = cv2.inRange(hsv, lower_red1, upper_red1)
        mask2 = cv2.inRange(hsv, lower_red2, upper_red2)
        red_mask = cv2.bitwise_or(mask1, mask2)
        
        # Find contours
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # Find the largest red contour (likely the mat boundary)
        if contours:
            largest_contour = max(contours, key=cv2.contourArea)
            area = cv2.contourArea(largest_contour)
            
            # Only accept if it's significantly large (workspace boundary)
            if area > 50000:  # Minimum area for workspace
                x, y, w, h = cv2.boundingRect(largest_contour)
                return (x, y, w, h)
        
        return None
    
    def detect_colored_objects(self, frame, use_roi=True):
        """
        Detect red, yellow, and blue objects in the frame.
        
        Args:
            frame: BGR image from camera
            use_roi: Whether to use the fixed ROI mask (default True)
            
        Returns:
            dict: Dictionary with detected objects by color
                {'red': [(x, y, w, h), ...], 'yellow': [...], 'blue': [...]}
        """
        if frame is None:
            return {}
        
        # Create ROI mask using fixed detection area
        roi_mask = None
        if use_roi and self.detection_roi is not None:
            x, y, w, h = self.detection_roi
            roi_mask = np.zeros(frame.shape[:2], dtype=np.uint8)
            roi_mask[y:y+h, x:x+w] = 255
        
        # Convert to HSV color space
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        detected_objects = {}
        kernel = np.ones((5, 5), np.uint8)
        
        # Define color ranges in HSV
        color_ranges = {
            'blue': [
                (np.array([100, 100, 100]), np.array([130, 255, 255]))
            ],
            'yellow': [
                (np.array([20, 100, 100]), np.array([30, 255, 255]))
            ]
        }
        
        for color_name, ranges in color_ranges.items():
            # Create mask for this color
            mask = None
            for lower, upper in ranges:
                if mask is None:
                    mask = cv2.inRange(hsv, lower, upper)
                else:
                    mask = cv2.bitwise_or(mask, cv2.inRange(hsv, lower, upper))
            
            # Apply ROI mask if provided
            if roi_mask is not None:
                mask = cv2.bitwise_and(mask, roi_mask)
            
            # Apply morphological operations to reduce noise
            kernel = np.ones((5, 5), np.uint8)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
            
            # Find contours
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # Filter contours by area and store bounding boxes
            objects = []
            for contour in contours:
                area = cv2.contourArea(contour)
                # Smaller objects only (exclude large boundary)
                if 500 < area < 30000:
                    x, y, w, h = cv2.boundingRect(contour)
                    objects.append((x, y, w, h, area))
            
            detected_objects[color_name] = objects
        
        # Add red object detection with area filtering
        red_ranges = [
            (np.array([0, 100, 100]), np.array([10, 255, 255])),
            (np.array([160, 100, 100]), np.array([180, 255, 255]))
        ]
        
        red_mask = None
        for lower, upper in red_ranges:
            if red_mask is None:
                red_mask = cv2.inRange(hsv, lower, upper)
            else:
                red_mask = cv2.bitwise_or(red_mask, cv2.inRange(hsv, lower, upper))
        
        # Apply ROI mask if provided
        if roi_mask is not None:
            red_mask = cv2.bitwise_and(red_mask, roi_mask)
        
        # Apply morphological operations
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_OPEN, kernel)
        red_mask = cv2.morphologyEx(red_mask, cv2.MORPH_CLOSE, kernel)
        
        # Find red contours
        contours, _ = cv2.findContours(red_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        red_objects = []
        for contour in contours:
            area = cv2.contourArea(contour)
            # Only small/medium red objects (not the mat boundary)
            if 500 < area < 30000:
                x, y, w, h = cv2.boundingRect(contour)
                red_objects.append((x, y, w, h, area))
        
        detected_objects['red'] = red_objects
        
        return detected_objects
    
    def draw_colored_objects(self, frame, detected_objects):
        """
        Draw bounding boxes around detected colored objects.
        
        Args:
            frame: BGR image to draw on
            detected_objects: Dictionary from detect_colored_objects()
            
        Returns:
            frame: Annotated frame with colored object bounding boxes
        """
        if frame is None or not detected_objects:
            return frame
        
        # Color BGR values for drawing
        draw_colors = {
            'red': (0, 0, 255),
            'blue': (255, 0, 0),
            'yellow': (0, 255, 255)
        }
        
        for color_name, objects in detected_objects.items():
            color = draw_colors.get(color_name, (255, 255, 255))
            for x, y, w, h, area in objects:
                # Draw rectangle
                cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
                
                # Calculate center
                cx = x + w // 2
                cy = y + h // 2
                
                # Draw center point
                cv2.circle(frame, (cx, cy), 5, color, -1)
                
                # Draw label
                label = f"{color_name.upper()}"
                cv2.putText(
                    frame,
                    label,
                    (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    color,
                    2
                )
        
        return frame
    
    def reset_detection(self):
        """Reset detection data."""
        self.confirmed_markers = {}
        self.detection_count = 0
        self.marker_5_robot_position = None
    
    def reset_calibration(self):
        """Reset calibration and all detection data."""
        self.confirmed_markers = {}
        self.detection_count = 0
        self.calibration_matrix = None
        self.is_calibrated = False
        self.marker_5_robot_position = None
