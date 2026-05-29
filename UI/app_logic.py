"""
SCARA Robot Controller - Business Logic Layer

This module contains all the robot control logic, state management,
and communication with the hardware.
"""

import time
import json
import os
import sys
import math

# Add parent directory to path to import robot modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_link import SerialLink
from motions import handshake, enable
from Robot_Command import Robot_command


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


class RobotController:
    """Business logic controller for SCARA robot operations"""
    
    def __init__(self, serial_link=None, log_callback=None, update_callback=None):
        """
        Initialize robot controller.
        
        Args:
            serial_link: SerialLink object for robot communication
            log_callback: Function to call for logging messages
            update_callback: Function to call to update UI during long operations
        """
        self.link = serial_link
        self.log = log_callback or print
        self.update_callback = update_callback
        
        # Axis command strings (updated when 'do' buttons are pressed)
        self.X_cmd = ""
        self.Y_cmd = ""
        self.Z_cmd = ""
        self.A_cmd = ""
        
       
        # self.Y_remain_max = 0  # Y axis remaining movement up (in steps)
        # self.Y_remain_min = 0  # Y axis remaining movement down (in steps)
        # self.X_remain_max = 0  # X axis remaining movement CW (in steps)
        # self.X_remain_min = 0  # X axis remaining movement CCW (in steps)
        # self.Z_remain_max = 0  # Z axis remaining movement CW (in steps)
        # self.Z_remain_min = 0  # Z axis remaining movement CCW (in steps)
        # self.A_remain_max = 0  # A axis remaining movement CW (in steps)
        # self.A_remain_min = 0  # A axis remaining movement CCW (in steps)

        # # Axis movement limiters (how much movement remaining in each direction)
        # # Updated after each movement if axis is homed
        self.remain_limits = {
            'Y': {'max': 0, 'min': 0},  
            'X': {'max': 0, 'min': 0},
            'Z': {'max': 0, 'min': 0},
            'A': {'max': 0, 'min': 0}   
        }
        
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
        
        self.max_x_Angle = 80
        self.max_z_Angle = 148

        # Absolute position tracking (first IK solution)
        self.absolute_position = {
            'x_cm': 0.0,           # Current X position in cm from base
            'y_cm': 0.0,           # Current Y position in cm from base
            'x_angle_deg': 0.0,    # Current X axis angle in degrees
            'z_angle_deg': 0.0,    # Current Z axis angle in degrees
            'x_direction': 'CW',   # Current X direction
            'z_direction': 'CW',   # Current Z direction
            'distance': 0.0,       # Current distance from base in cm
            'y_axis_cm': 0.0,      # Current Y axis position in cm
            'is_valid': False      # True after first successful move to position
        }   
        
        # Secondary absolute position tracking (second IK solution)
        self.sec_absolute_position = {
            'x_cm': 0.0,           # Current X position in cm from base
            'y_cm': 0.0,           # Current Y position in cm from base
            'x_angle_deg': 0.0,    # Current X axis angle in degrees
            'z_angle_deg': 0.0,    # Current Z axis angle in degrees
            'x_direction': 'CW',   # Current X direction
            'z_direction': 'CW',   # Current Z direction
            'distance': 0.0,       # Current distance from base in cm
            'y_axis_cm': 0.0,      # Current Y axis position in cm
            'is_valid': False      # True after first successful move to position
        }
        
        # Movement angles (final angles to be executed)
        self.movement_angles = {
            'x_cm': 0.0,           # Target X position in cm
            'y_cm': 0.0,           # Target Y position in cm
            'x_angle_deg': 0.0,    # X axis movement angle in degrees
            'z_angle_deg': 0.0,    # Z axis movement angle in degrees
            'x_direction': 'CW',   # X movement direction
            'z_direction': 'CW',   # Z movement direction
            'distance': 0.0,       # Distance from base in cm
            'y_axis_cm': 0.0,      # Y axis movement in cm
            'is_valid': False      # True after movement angles are calculated
        }
        # Last position tracking (for inverse kinematics optimization)
        self.last_position = {
            'x_cm': 0.0,           # Last X position in cm
            'y_cm': 0.0,           # Last Y position in cm
            'x_angle_deg': 0.0,    # Last X axis angle in degrees
            'z_angle_deg': 0.0,    # Last Z axis angle in degrees
            'x_direction': 'CW',   # Last X direction
            'z_direction': 'CW',   # Last Z direction
            'distance': 0.0,       # Last distance from base
            'y_axis_cm': 0.0,      # Last Y axis position in cm
            'is_valid': True      # True after first successful move to position
        }
        self.preferred_solution = {
            'x_angle_deg': 0.0,    # Preferred X angle in degrees
            'z_angle_deg': 0.0,    # Preferred Z angle in degrees
            'x_direction': 'CW',   # Preferred X direction
            'z_direction': 'CW',   # Preferred Z direction
            'distance': 0.0,       # Distance from base in cm
            'y_axis_cm': 0.0,      # Y axis position in cm
            'is_valid': False      # True if preferred solution is valid
        }
        
        # Load axis configuration
        self.axis_config = load_axis_config()
        
        # Store axis limits from configuration
        self.axis_limits = {
            'X': {'min': 0, 'max': 150},
            'Y': {'min': 0, 'max': 10},
            'Z': {'min': 0, 'max': 280},
            'A': {'min': 0, 'max': 150}
        }

        self.axis_steps_per_unit = {
            'X': 1,
            'Y': 1,
            'Z': 1,
            'A': 1
        }

        self.load_axis_data()
        
        # # Legacy variables for backward compatibility
        # self.y_min_limit = self.axis_limits['Y']['min']
        # self.y_max_limit = self.axis_limits['Y']['max']
        # self.x_min_limit = self.axis_limits['X']['min']
        # self.x_max_limit = self.axis_limits['X']['max'] 
        # self.z_min_limit = self.axis_limits['Z']['min']
        # self.z_max_limit = self.axis_limits['Z']['max'] 
        # self.a_min_limit = self.axis_limits['A']['min']
        # self.a_max_limit = self.axis_limits['A']['max'] 

        # self.y_steps_per_unit = self.axis_steps_per_unit['Y']
        # self.x_steps_per_unit = self.axis_steps_per_unit['X']   
        # self.z_steps_per_unit = self.axis_steps_per_unit['Z'] 
        # self.a_steps_per_unit = self.axis_steps_per_unit['A']

    def update_axis_position_after_home(self):
        # After homing, we know the exact position of the robot (at the limit switch), so we can update our absolute position tracking accordingly.

        self.absolute_position = {
            'x_cm': -9.82,           # Current X position in cm from base
            'y_cm': 12.001,           # Current Y position in cm from base
            'x_angle_deg': 78.04,    # Current X axis angle in degrees
            'z_angle_deg': 137.81,    # Current Z axis angle in degrees
            'x_direction': 'CCW',   # Current X direction
            'z_direction': 'CW',   # Current Z direction
            'distance': 15.51,       # Current distance from base in cm
            'y_axis_cm': 0.0,      # Current Y axis position in cm
            'is_valid': True      # True after first successful move to position
        }   
        
        # Secondary absolute position tracking (second IK solution)
        self.sec_absolute_position = {
            'x_cm': -9.82,           # Current X position in cm from base
            'y_cm': 12.001,           # Current Y position in cm from base
            'x_angle_deg': 0.55,    # Current X axis angle in degrees
            'z_angle_deg': 137.81,    # Current Z axis angle in degrees
            'x_direction': 'CCW',   # Current X direction
            'z_direction': 'CCW',   # Current Z direction
            'distance': 15.51,       # Current distance from base in cm
            'y_axis_cm': 0.0,      # Current Y axis position in cm
            'is_valid': True      # True after first successful move to position
        }
        
        # Movement angles (final angles to be executed)
        self.movement_angles = {
            'x_cm': -9.82,           # Target X position in cm
            'y_cm': 12.001,           # Target Y position in cm
            'x_angle_deg': 78.04,    # X axis movement angle in degrees
            'z_angle_deg': 137.81,    # Z axis movement angle in degrees
            'x_direction': 'CCW',   # X movement direction
            'z_direction': 'CW',   # Z movement direction
            'distance': 15.51,       # Distance from base in cm
            'y_axis_cm': 0.0,      # Y axis movement in cm
            'is_valid': True      # True after movement angles are calculated
        }
        # Last position tracking (for inverse kinematics optimization)
        self.last_position = {
            'x_cm': -9.82,           # Last X position in cm
            'y_cm': 12.001,           # Last Y position in cm
            'x_angle_deg': 78.04,    # Last X axis angle in degrees
            'z_angle_deg': 137.81,    # Last Z axis angle in degrees
            'x_direction': 'CCW',   # Last X direction
            'z_direction': 'CW',   # Last Z direction
            'distance': 15.51,       # Last distance from base
            'y_axis_cm': 0.0,      # Last Y axis position in cm
            'is_valid': True      # True after first successful move to position
        }
        self.preferred_solution = {
            'x_angle_deg': 78.04,    # Preferred X angle in degrees
            'z_angle_deg': 137.81,    # Preferred Z angle in degrees
            'x_direction': 'CCW',   # Preferred X direction
            'z_direction': 'CW',   # Preferred Z direction
            'distance': 15.51,       # Distance from base in cm
            'y_axis_cm': 0.0,      # Y axis position in cm
            'is_valid': True      # True if preferred solution is valid
        }


        
    def load_axis_data(self):
        """Load axis limits from configuration"""
        if self.axis_config and 'axes' in self.axis_config:
            for axis in ['X', 'Y', 'Z', 'A']:
                axis_data = self.axis_config['axes'].get(axis, {})
                self.axis_limits[axis]['min'] = axis_data.get('min_limit', 0)
                self.axis_limits[axis]['max'] = axis_data.get('max_limit', 1000)
                self.remain_limits[axis]['min'] = self.axis_limits[axis]['min']
                self.remain_limits[axis]['max'] = self.axis_limits[axis]['max']
                self.axis_steps_per_unit[axis] = axis_data.get('steps_per_unit', 1)
    
    def get_axis_defaults(self, axis_name):
        """Get default speed and direction for an axis from config"""
        if not self.axis_config or 'axes' not in self.axis_config:
            return 500, 1, 1, 0, 1000  # Fallback defaults
        
        axis_data = self.axis_config['axes'].get(axis_name.upper(), {})
        default_speed = axis_data.get('default_speed', 500)
        default_direction = axis_data.get('default_direction', 1)
        default_steps_per_unit = axis_data.get('steps_per_unit', 1)
        min_limit = axis_data.get('min_limit', 0)
        max_limit = axis_data.get('max_limit', 1000)
        
        return default_speed, default_direction, default_steps_per_unit, min_limit, max_limit
    
    def get_last_position(self):
        """
        Get the last known position of the robot.
        
        Returns:
            dict: Last position data containing:
                - x_cm: Last X position in cm
                - y_cm: Last Y position in cm
                - x_angle_deg: Last X axis angle in degrees
                - z_angle_deg: Last Z axis angle in degrees
                - x_direction: Last X direction ('CW' or 'CCW')
                - z_direction: Last Z direction ('CW' or 'CCW')
                - distance: Last distance from base in cm
                - is_valid: True if position has been set, False if no valid position yet
        """
        return self.last_position.copy()
    
    def reset_remain_limits(self):
        """Reset remain limits to original values from configuration."""
        for axis in ['X', 'Y', 'Z', 'A']:
            self.remain_limits[axis]['min'] = self.axis_limits[axis]['min']
            self.remain_limits[axis]['max'] = self.axis_limits[axis]['max']
        
        self.log("[Limits] Remain limits reset to config values")
    
    def inverse_kinematics(self, target_x_cm, target_y_cm):
        """
        Calculate inverse kinematics for 2-link SCARA arm.
        
        Calculates both absolute target angles and relative movements from last position.
        If a valid last position exists, returns the relative movement needed.
        Otherwise, returns absolute movement from zero position.
        
        Base coordinate system (shoulder joint at origin):
        - Origin (0,0) at shoulder joint (base of robot)
        - Positive X = right
        - Positive Y = forward/away from base
        
        Args:
            target_x_cm: Target X position in cm from base (shoulder joint)
            target_y_cm: Target Y position in cm from base (shoulder joint)
        
        Returns:
            dict: {
                'success': bool,
                'x_angle_deg': float,  # Movement angle to execute (relative or absolute)
                'z_angle_deg': float,  # Movement angle to execute (relative or absolute)
                'x_angle_direction': str,  # Movement direction ("CW" or "CCW")
                'z_angle_direction': str,  # Movement direction ("CW" or "CCW")
                'absolute_x_angle_deg': float,  # Target absolute position angle
                'absolute_z_angle_deg': float,  # Target absolute position angle
                'absolute_x_direction': str,    # Target absolute direction
                'absolute_z_direction': str,    # Target absolute direction
                'x_steps': int,        # X axis movement in steps
                'z_steps': int,        # Z axis movement in steps
                'message': str         # Status or error message
            }
        """
        # Get robot geometry from config
        quater = 1
        if not self.axis_config or 'robot_geometry' not in self.axis_config:
            return {
                'success': False,
                'x_angle_deg': 0,
                'x_angle_direction': "CW",
                'z_angle_deg': 0,
                'z_angle_direction': "CW",
                'x_steps': 0,
                'z_steps': 0,
                'message': 'Robot geometry not defined in axis_config.json'
            }
        
        geometry = self.axis_config['robot_geometry']
        L1 = geometry.get('arm_link_1_length_cm', 25.0)  # First arm (shoulder to elbow)
        L2 = geometry.get('arm_link_2_length_cm', 15.0)  # Second arm (elbow to end effector)
        
        # DEBUG: Log the arm lengths being used
        self.log(f"[IK DEBUG] Using L1={L1}cm, L2={L2}cm")
        self.log(f"[IK DEBUG] Target base coords: ({target_x_cm}, {target_y_cm})")
        
        # Use coordinates directly as base coordinates (no transformation)
        x_base = target_x_cm
        y_base = target_y_cm
        
        self.log(f"[IK DEBUG] Base coords: ({x_base:.2f}, {y_base:.2f})")
        
        # Calculate distance from base to target
        r = math.sqrt(x_base**2 + y_base**2)
        
        # Check if target is reachable
        max_reach = L1 + L2
        min_reach = abs(L1 - L2)
        
        if r > max_reach:
            return {
                'success': False,
                'x_angle_deg': 0,
                'z_angle_deg': 0,
                'x_angle_direction': "CW",
                'z_angle_direction': "CW",
                'x_steps': 0,
                'z_steps': 0,
                'message': f'Target too far! Distance from base: {r:.2f}cm, Max reach: {max_reach:.2f}cm'
            }
        
        if r < min_reach:
            return {
                'success': False,
                'x_angle_deg': 0,
                'z_angle_deg': 0,
                'x_angle_direction': "CW",
                'z_angle_direction': "CW",
                'x_steps': 0,
                'z_steps': 0,
                'message': f'Target too close! Distance from base: {r:.2f}cm, Min reach: {min_reach:.2f}cm'
            }
        # calculate the absulte triangle angels using law of cosines
        shoulder_angle_deg =  math.degrees(math.acos((r**2 + L1**2 - L2**2) / (2 * L1 * r)))
        elbow_angle_deg = math.degrees(math.acos((L1**2 + L2**2 - r**2) / (2 * L1 * L2)))
        target_angle_deg = 180 - shoulder_angle_deg - elbow_angle_deg
        
        
        # claluclate the shoulder movmnent 
        shoulder_angle_for_X_Axis = math.degrees(math.acos(target_x_cm/r))
        sholder_angle_for_y_Axis = math.degrees(math.acos(target_y_cm/r))
        shoulder_movment_angle_for_Y_Axis = 90 - shoulder_angle_for_X_Axis - shoulder_angle_deg
        seco_shoulder_movment_angle_for_Y_Axis = shoulder_movment_angle_for_Y_Axis + 2 * shoulder_angle_deg
        if shoulder_movment_angle_for_Y_Axis >= 0:
            x_angle_direction = "CW"
        else:
            x_angle_direction = "CCW"
        if seco_shoulder_movment_angle_for_Y_Axis >= 0:
            x_sec_angle_direction = "CW"
        else:
            x_sec_angle_direction = "CCW"


        # claluclate the elbow movmnent 
        shoulder_angle_deg = 180 - elbow_angle_deg
    
        z_angle_direction = "CW"
        z_sec_angle_direction = "CCW"


        # Update absolute_position dictionary (first IK solution)
        self.absolute_position['x_cm'] = target_x_cm
        self.absolute_position['y_cm'] = target_y_cm
        self.absolute_position['x_angle_deg'] = abs(shoulder_movment_angle_for_Y_Axis)
        self.absolute_position['x_direction'] = x_angle_direction
        self.absolute_position['z_angle_deg'] = shoulder_angle_deg
        self.absolute_position['z_direction'] = z_angle_direction
        self.absolute_position['distance'] = r
        self.absolute_position['is_valid'] = True

        if self.absolute_position['x_angle_deg']  >  self.max_x_Angle:
            self.absolute_position['is_valid'] = False
            self.log(f"[IK DEBUG] First solution INVALID: X angle {self.absolute_position['x_angle_deg']:.2f}° > max {self.max_x_Angle}°")
        if self.absolute_position['z_angle_deg']  >  self.max_z_Angle:
            self.absolute_position['is_valid'] = False
            self.log(f"[IK DEBUG] First solution INVALID: Z angle {self.absolute_position['z_angle_deg']:.2f}° > max {self.max_z_Angle}°")


        # Update sec_absolute_position dictionary (second IK solution - shoulder on the right)
        self.sec_absolute_position['x_cm'] = target_x_cm
        self.sec_absolute_position['y_cm'] = target_y_cm
        self.sec_absolute_position['x_angle_deg'] = abs(seco_shoulder_movment_angle_for_Y_Axis)
        self.sec_absolute_position['x_direction'] = x_sec_angle_direction
        self.sec_absolute_position['z_angle_deg'] = shoulder_angle_deg
        self.sec_absolute_position['z_direction'] = z_sec_angle_direction
        self.sec_absolute_position['distance'] = r
        self.sec_absolute_position['is_valid'] = True

        if self.sec_absolute_position['x_angle_deg']  >  self.max_x_Angle:
            self.sec_absolute_position['is_valid'] = False
            self.log(f"[IK DEBUG] Second solution INVALID: X angle {self.sec_absolute_position['x_angle_deg']:.2f}° > max {self.max_x_Angle}°")
        if self.sec_absolute_position['z_angle_deg']  >  self.max_z_Angle:
            self.sec_absolute_position['is_valid'] = False
            self.log(f"[IK DEBUG] Second solution INVALID: Z angle {self.sec_absolute_position['z_angle_deg']:.2f}° > max {self.max_z_Angle}°")


        self.log(f"[IK DEBUG] first solution : absolute_x_angle: {self.absolute_position['x_angle_deg']:.2f}° ({self.absolute_position['x_direction']}), absolute_z_angle: {self.absolute_position['z_angle_deg']:.2f}° ({self.absolute_position['z_direction']}), is_valid={self.absolute_position['is_valid']}")
        self.log(f"[IK DEBUG] second solution : absolute_x_angle: {self.sec_absolute_position['x_angle_deg']:.2f}° ({self.sec_absolute_position['x_direction']}), absolute_z_angle: {self.sec_absolute_position['z_angle_deg']:.2f}° ({self.sec_absolute_position['z_direction']}), is_valid={self.sec_absolute_position['is_valid']}")
        

        if self.absolute_position['is_valid'] ==True:
            self.preferred_solution['x_angle_deg'] = self.absolute_position['x_angle_deg']
            self.preferred_solution['x_direction'] = self.absolute_position['x_direction']
            self.preferred_solution['z_angle_deg'] = self.absolute_position['z_angle_deg']
            self.preferred_solution['z_direction'] = self.absolute_position['z_direction']
            self.preferred_solution['distance'] = self.absolute_position['distance']
            self.preferred_solution['is_valid'] = True
        elif self.sec_absolute_position['is_valid'] ==True and self.absolute_position['is_valid'] ==False:
            self.preferred_solution['x_angle_deg'] = self.sec_absolute_position['x_angle_deg']
            self.preferred_solution['x_direction'] = self.sec_absolute_position['x_direction']
            self.preferred_solution['z_angle_deg'] = self.sec_absolute_position['z_angle_deg']
            self.preferred_solution['z_direction'] = self.sec_absolute_position['z_direction']
            self.preferred_solution['distance'] = self.sec_absolute_position['distance']
            self.preferred_solution['is_valid'] = True
        else:
            self.preferred_solution['x_angle_deg'] = 0.0
            self.preferred_solution['x_direction'] = "CW"
            self.preferred_solution['z_angle_deg'] = 0.0
            self.preferred_solution['z_direction'] = "CW"
            self.preferred_solution['distance'] = r
            self.preferred_solution['is_valid'] = False




        # Calculate relative movement from last position if available
        if self.last_position['is_valid'] and self.preferred_solution['is_valid']:
            self.log(f"[IK] Last position valid - calculating relative movement")
            self.log(f"[IK] Last X: {self.last_position['x_angle_deg']:.2f}° {self.last_position['x_direction']}, Last Z: {self.last_position['z_angle_deg']:.2f}° {self.last_position['z_direction']}")
            
            # Calculate absolute positions (converting to signed values)
            # CW is positive, CCW is negative for calculation purposes
            last_x_absolute = self.last_position['x_angle_deg'] if self.last_position['x_direction'] == 'CW' else -self.last_position['x_angle_deg']
            last_z_absolute = self.last_position['z_angle_deg'] if self.last_position['z_direction'] == 'CW' else -self.last_position['z_angle_deg']
            
            new_x_absolute =  self.preferred_solution['x_angle_deg'] if self.preferred_solution['x_direction'] == 'CW' else -self.preferred_solution['x_angle_deg']
            new_z_absolute = self.preferred_solution['z_angle_deg'] if self.preferred_solution['z_direction'] == 'CW' else -self.preferred_solution['z_angle_deg']
            
            # Calculate differences (relative movement needed)
            x_diff = new_x_absolute - last_x_absolute
            z_diff = new_z_absolute - last_z_absolute
            
            # Convert back to magnitude and direction
            x_relative_magnitude = abs(x_diff)
            x_relative_direction = 'CW' if x_diff >= 0 else 'CCW'
            
            z_relative_magnitude = abs(z_diff)
            z_relative_direction = 'CW' if z_diff >= 0 else 'CCW'
            
            self.log(f"[IK] Relative movement - X: {x_relative_magnitude:.2f}° {x_relative_direction}, Z: {z_relative_magnitude:.2f}° {z_relative_direction}")
            
            # Use relative movements for execution
            final_x_angle = x_relative_magnitude
            final_x_direction = x_relative_direction
            final_z_angle = z_relative_magnitude
            final_z_direction = z_relative_direction
            message_prefix = "Relative"
           

        else:
            # No valid last position - use absolute movements
            self.log(f"[IK] No valid last position - using absolute movement from zero")
            final_x_angle = self.preferred_solution['x_angle_deg']
            final_x_direction = self.preferred_solution['x_direction']
            final_z_angle = self.preferred_solution['z_angle_deg']
            final_z_direction = self.preferred_solution['z_direction']
            message_prefix = "Absolute"
        
        # Note: Do not update last_position here!
        # It should only be updated by move_to_position() after successful movement
        
        # Update movement_angles dictionary with final calculated movement
        self.movement_angles['x_cm'] = target_x_cm
        self.movement_angles['y_cm'] = target_y_cm
        self.movement_angles['x_angle_deg'] = final_x_angle
        self.movement_angles['x_direction'] = final_x_direction
        self.movement_angles['z_angle_deg'] = final_z_angle
        self.movement_angles['z_direction'] = final_z_direction
        self.movement_angles['distance'] = r
        self.movement_angles['is_valid'] = True

        return {
                'success': True,
                'x_angle_deg': final_x_angle,                    # Movement angle to execute
                'z_angle_deg': final_z_angle,                    # Movement angle to execute
                'x_angle_direction': final_x_direction,          # Movement direction to execute
                'z_angle_direction': final_z_direction,          # Movement direction to execute
                'absolute_x_angle_deg': self.absolute_position['x_angle_deg'],        # Target absolute position
                'absolute_z_angle_deg': self.absolute_position['z_angle_deg'],        # Target absolute position
                'absolute_x_direction': self.absolute_position['x_direction'],    # Target absolute direction
                'absolute_z_direction': self.absolute_position['z_direction'],    # Target absolute direction
                'x_steps': 0,
                'z_steps': 0,
                'message': f'IK Success ({message_prefix}): X={final_x_angle:.2f}° ({final_x_direction}), Z={final_z_angle:.2f}° ({final_z_direction})'
            }
       
    
    def update_axis_command(self, axis_name, cmd):
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
            return False
    
    def update_limiters_value(self, axis, cmd,):
        """Update limiter values based on movement command"""
        homestate = getattr(self, f"{axis}_homing_status", False)

        if homestate == True: 
            cmd_value = abs(int(cmd.split(" ")[1]) / self.axis_steps_per_unit[axis])

            self.remain_limits[axis]['max'] = self.remain_limits[axis]['max'] - cmd_value
            self.remain_limits[axis]['min'] = self.remain_limits[axis]['min'] + cmd_value

    
    def query_stopper_status(self, axis):
        """
        Query stopper status from robot for a specific axis.
        
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
            return False
    
    def query_all_stopper_status(self):
        """
        Query and return stopper status for all axes.
        
        Returns:
            dict: Stopper status for each axis {'X': bool, 'Y': bool, 'Z': bool, 'A': bool}
        """
        status = {}
        for axis in ['Y', 'X', 'Z', 'A']:
            is_pressed = self.query_stopper_status(axis)
            status[axis] = is_pressed
            # Update internal state
            setattr(self, f"{axis}_stopper_status", is_pressed)
        return status
    
    def execute_movement(self, axis_name, cmd, timeout_s=None):
        """
        Execute a movement command for a single axis.
        
        Args:
            axis_name: Name of axis ('X', 'Y', 'Z', or 'A')
            cmd: Command string
            timeout_s: Optional timeout override
        
        Returns:
            dict: {'success': bool, 'stopper_hit': bool, 'response': str}
        """
        if not self.link:
            self.log("[Movement] ERROR: Not connected to robot")
            return {'success': False, 'stopper_hit': False, 'response': 'Not connected'}
        
        try:
            # Query stopper status BEFORE movement to detect if already pressed
            pre_stopper_status = self.query_stopper_status(axis_name)
            if pre_stopper_status:
                self.log(f"[Movement] WARNING: {axis_name} stopper is ALREADY PRESSED before movement!")
            else:
                self.log(f"[Movement] {axis_name} stopper status before movement: OK (not pressed)")
            
            start_time = time.time()
            
            self.log(f"[Movement] Executing on {axis_name}: {cmd}")
            response = Robot_command(cmd, self.link, self.log)
            
            # Calculate timeout based on movement.
            # With accel/decel enabled in firmware, real duration is higher than constant-speed time.
            # Add conservative margin for ramp phases and MCU scheduling overhead.
            cmd_steps = abs(int(cmd.split(" ")[1]))
            cmd_speed = max(1, abs(int(cmd.split(" ")[2])))
            base_time = cmd_steps / cmd_speed
            calc_time = (base_time * 2.2) + 2.0
            timeout = timeout_s if timeout_s is not None else calc_time
            
            movement_done = False
            stopper_hit = False
            done_response = ""
            
            self.log(f"[Movement] Waiting for completion on {axis_name} (timeout: {timeout}s)")
            
            # Poll for completion within timeout
            while (time.time() - start_time) < timeout:
                try:
                    # Read response from robot (non-blocking)
                    done_response = self.link.ser.readline().decode(errors="ignore").strip()
                    
                    if done_response == "R:OK done":
                        movement_done = True
                        self.log(f"[Movement] {axis_name} completed successfully in {int(time.time() - start_time)}s (calc time: {calc_time}s)")
                        break
                    elif "STOPPER_HIT" in done_response or "R:ERR" in done_response:
                        self.log(f"[Movement] {axis_name} error: {done_response}")
                        if "STOPPER_HIT" in done_response:
                            stopper_hit = True
                            # Immediately verify stopper status when hit is reported
                            time.sleep(0.2)  # Small delay to let robot settle
                            actual_status = self.query_stopper_status(axis_name)
                            if actual_status:
                                self.log(f"[Movement] {axis_name} stopper VERIFIED: Pin is actually pressed (=1)")
                            else:
                                self.log(f"[Movement] {axis_name} stopper MISMATCH: Firmware reported hit but pin reads NOT pressed (=0) - possible false trigger!")
                        break
                    elif done_response and done_response != "":
                        self.log(f"[Movement] {axis_name} received: {done_response}")
                        
                except Exception as e:
                    self.log(f"[Movement] Read error: {e}")
                    break
                
                # Update UI to keep it responsive (allows E-Stop to be pressed)
                if self.update_callback:
                    try:
                        self.update_callback()
                    except:
                        pass  # Ignore UI update errors
                
                # Small delay to avoid busy-waiting
                time.sleep(0.1)
            
            # Check result
            if not movement_done and not stopper_hit:
                self.log(f"[Movement] {axis_name} TIMEOUT - no completion after {timeout}s")
            
            # Query stopper status after movement for final verification
            is_pressed = self.query_stopper_status(axis_name)
            setattr(self, f"{axis_name}_stopper_status", is_pressed)
            self.log(f"[Movement] {axis_name} final stopper status: {'PRESSED (=1)' if is_pressed else 'NOT PRESSED (=0)'}")
            
            # IMPORTANT: Clear command after execution (success or failure)
            # This prevents old commands from lingering after stopper hits
            self.update_axis_command(axis_name, "")
            
            return {
                'success': movement_done,
                'stopper_hit': stopper_hit,
                'response': done_response
            }
            
        except Exception as e:
            self.log(f"[Movement] ERROR on {axis_name}: {e}")
            return {'success': False, 'stopper_hit': False, 'response': str(e)}

    def execute_xz_movement(self, x_steps_signed, z_steps_signed, x_speed, z_speed, timeout_s=None):
        """
        Execute coordinated X and Z movement using the XZSTEP firmware command.

        Args:
            x_steps_signed: Signed steps for X axis (negative = reverse direction)
            z_steps_signed: Signed steps for Z axis (negative = reverse direction)
            x_speed: X axis speed in steps/sec
            z_speed: Z axis speed in steps/sec
            timeout_s: Optional timeout override in seconds

        Returns:
            dict: {'success': bool, 'stopper_hit': bool, 'response': str}
        """
        if not self.link:
            self.log("[XZ] ERROR: Not connected to robot")
            return {'success': False, 'stopper_hit': False, 'response': 'Not connected'}

        x_steps = abs(x_steps_signed)
        z_steps = abs(z_steps_signed)
        x_dir = 1 if x_steps_signed >= 0 else -1
        z_dir = 1 if z_steps_signed >= 0 else -1

        cmd = f"XZSTEP {x_steps} {z_steps} {x_speed} {z_speed} {x_dir} {z_dir}"
        self.log(f"[XZ] Sending coordinated command: '{cmd}'")

        try:
            from protocol import ask
            response = ask(self.link, cmd)
            self.log(f"[XZ] Initial response: {response}")

            # Calculate timeout from the slower axis with accel/decel margin.
            base_time = max(x_steps / max(1, x_speed), z_steps / max(1, z_speed))
            calc_time = (base_time * 2.2) + 2.0
            timeout = timeout_s if timeout_s is not None else calc_time

            start_time = time.time()
            movement_done = False
            stopper_hit = False
            done_response = ""

            self.log(f"[XZ] Waiting for completion (timeout: {timeout:.1f}s)")

            while (time.time() - start_time) < timeout:
                try:
                    done_response = self.link.ser.readline().decode(errors="ignore").strip()

                    if done_response == "R:OK done":
                        movement_done = True
                        self.log(f"[XZ] Coordinated movement completed in {time.time() - start_time:.1f}s")
                        break
                    elif "STOPPER_HIT" in done_response or "R:ERR" in done_response:
                        self.log(f"[XZ] Error/stopper: {done_response}")
                        stopper_hit = "STOPPER_HIT" in done_response
                        # Update stopper status for affected axis
                        if "X" in done_response:
                            self.X_stopper_status = True
                        if "Z" in done_response:
                            self.Z_stopper_status = True
                        break
                    elif done_response:
                        self.log(f"[XZ] Received: {done_response}")

                except Exception as e:
                    self.log(f"[XZ] Read error: {e}")
                    break

                if self.update_callback:
                    try:
                        self.update_callback()
                    except Exception:
                        pass

                time.sleep(0.1)

            if not movement_done and not stopper_hit:
                self.log(f"[XZ] TIMEOUT - no completion after {timeout:.1f}s")

            # Final stopper verification
            self.X_stopper_status = self.query_stopper_status('X')
            self.Z_stopper_status = self.query_stopper_status('Z')

            return {
                'success': movement_done,
                'stopper_hit': stopper_hit,
                'response': done_response
            }

        except Exception as e:
            self.log(f"[XZ] ERROR: {e}")
            return {'success': False, 'stopper_hit': False, 'response': str(e)}

    def execute_all_movements(self):
        """
        Execute all queued axis commands.
        
        Returns:
            dict: Results for each axis that was executed
        """
        # List of axis commands in order
        axis_commands = [
            ('X', self.X_cmd),
            ('Y', self.Y_cmd),
            ('Z', self.Z_cmd),
            ('A', self.A_cmd)
        ]
        
        results = {}
        
        # Execute each non-empty command in order
        for axis_name, cmd in axis_commands:
            if cmd:  # Only execute if command is not empty
                result = self.execute_movement(axis_name, cmd)
                results[axis_name] = result
                
                # Update limiters if movement was successful
                if result['success'] :
                    homestate = getattr(self, f"{axis_name}_homing_status", False)
                    if homestate:
                        self.update_limiters_value(axis_name, cmd)
                
                # Note: Command is automatically cleared inside execute_movement()
        
        return results
    
    def move_to_position(self, target_x_cm, target_y_cm, speed=None):
        """
        Move end effector to target (x, y) position using inverse kinematics.
        
        Args:
            target_x_cm: Target X position in cm
            target_y_cm: Target Y position in cm
            speed: Optional speed override (steps/sec)
        
        Returns:
            dict: IK result with movement status
        """
        # Calculate inverse kinematics
        ik_result = self.inverse_kinematics(target_x_cm, target_y_cm)
        
        if not ik_result['success']:
            self.log(f"[IK] {ik_result['message']}")
            return ik_result
        
        # Log the calculated angles
        self.log(f"[IK] Target: ({target_x_cm:.2f}, {target_y_cm:.2f}) cm")
        self.log(f"[IK] Angles: X={ik_result['x_angle_deg']:.2f}°, Z={ik_result['z_angle_deg']:.2f}°")
        self.log(f"[IK] Steps: X={ik_result['x_steps']}, Z={ik_result['z_steps']}")
        
        # Calculate Y-axis (vertical) position
        # Y coordinate represents vertical distance from zero position
        # Zero position: -8000 steps, steps_per_cm: 1000
        y_zero_steps = -8000
        y_steps_per_cm = self.axis_steps_per_unit.get('Y', 1000)
        y_steps = y_zero_steps + int(target_y_cm * y_steps_per_cm)
        
        
        # Use default speeds if not specified
        if speed is None:
            x_speed = self.axis_config['axes']['X'].get('default_speed', 2000)
            z_speed = self.axis_config['axes']['Z'].get('default_speed', 2000)
        else:
            x_speed = y_speed = z_speed = speed
        
        # Clear any existing X and Z commands
        self.update_axis_command('X', "")
        self.update_axis_command('Z', "")
        
        # Get movement angles and directions from IK result
        x_angle_deg = ik_result['x_angle_deg']
        z_angle_deg = ik_result['z_angle_deg']
        x_direction = ik_result['x_angle_direction']
        z_direction = ik_result['z_angle_direction']

        #building X command with direction
        if x_direction == "CW":
            x_movement_value = int(float(x_angle_deg) * self.axis_steps_per_unit.get('X', 1)   )
        else:
            x_movement_value = int(float(x_angle_deg) * self.axis_steps_per_unit.get('X', 1)   ) * (-1)
        
        #building Z command with direction
        if z_direction == "CW":
            z_movement_value = int(float(z_angle_deg) * self.axis_steps_per_unit.get('Z', 1)   )    
        else:
            z_movement_value = int(float(z_angle_deg) * self.axis_steps_per_unit.get('Z', 1)   ) * (-1)
        
        self.log(f"[IK] X movement value: {x_movement_value} steps ({x_direction})")
        self.log(f"[IK] Z movement value: {z_movement_value} steps ({z_direction})")

        # Execute X and Z together using coordinated XZSTEP, fall back to individual if only one axis moves
        movement_results = {}
        if x_movement_value != 0 and z_movement_value != 0:
            self.log(f"[IK] Using coordinated XZSTEP: X={x_movement_value} @ {x_speed} sps, Z={z_movement_value} @ {z_speed} sps")
            xz_result = self.execute_xz_movement(x_movement_value, z_movement_value, x_speed, z_speed)
            movement_results['X'] = xz_result
            movement_results['Z'] = xz_result
        else:
            # Fall back to individual axis commands for single-axis moves
            if x_movement_value != 0:
                x_cmd = f"X {x_movement_value} {x_speed}"
                self.update_axis_command('X', x_cmd)
                self.log(f"[IK] X-only movement command: '{x_cmd}'")
            else:
                self.log(f"[IK] X movement skipped (0 steps)")

            if z_movement_value != 0:
                z_cmd = f"Z {z_movement_value} {z_speed}"
                self.update_axis_command('Z', z_cmd)
                self.log(f"[IK] Z-only movement command: '{z_cmd}'")
            else:
                self.log(f"[IK] Z movement skipped (0 steps)")

            movement_results = self.execute_all_movements()

        # Check if all movements were successful
        # If no movements (all 0), consider it a success
        if len(movement_results) == 0:
            all_success = True
            self.log("[IK] No movement needed - already at target position")
        else:
            all_success = all(result.get('success', False) for result in movement_results.values())
        
        # Update last position ONLY if movement was successful
        # Use the preferred_solution (the one that was actually used for movement)
        if all_success:
            self.last_position['x_cm'] = target_x_cm
            self.last_position['y_cm'] = target_y_cm
            self.last_position['x_angle_deg'] = self.preferred_solution['x_angle_deg']
            self.last_position['z_angle_deg'] = self.preferred_solution['z_angle_deg']
            self.last_position['x_direction'] = self.preferred_solution['x_direction']
            self.last_position['z_direction'] = self.preferred_solution['z_direction']
            self.last_position['distance'] = self.preferred_solution['distance']
            self.last_position['is_valid'] = True
            
            self.log(f"[IK] Last position updated: ({target_x_cm:.2f}, {target_y_cm:.2f}) cm")
            self.log(f"[IK] Preferred solution stored: X={self.last_position['x_angle_deg']:.2f}° {self.last_position['x_direction']}, Z={self.last_position['z_angle_deg']:.2f}° {self.last_position['z_direction']}")
        
        # Return combined result with IK data and movement results
        # Use the movement angles/directions for display (these are what was executed)
        return {
            'success': all_success,
            'x_angle_deg': ik_result['x_angle_deg'],              # Relative movement executed
            'z_angle_deg': ik_result['z_angle_deg'],              # Relative movement executed
            'x_angle_direction': ik_result['x_angle_direction'],  # Movement direction
            'z_angle_direction': ik_result['z_angle_direction'],  # Movement direction
            'absolute_x_angle_deg': ik_result.get('absolute_x_angle_deg', ik_result['x_angle_deg']),
            'absolute_z_angle_deg': ik_result.get('absolute_z_angle_deg', ik_result['z_angle_deg']),
            'absolute_x_direction': ik_result.get('absolute_x_direction', ik_result['x_angle_direction']),
            'absolute_z_direction': ik_result.get('absolute_z_direction', ik_result['z_angle_direction']),
            'x_steps': ik_result['x_steps'],
            'z_steps': ik_result['z_steps'],
            'message': 'Movement completed successfully' if all_success else 'Movement failed',
            'movement_results': movement_results
        }
    
    def test_inverse_kinematics(self, target_x_cm, target_y_cm):
        """
        Test inverse kinematics without moving the robot.
        Just calculates and logs the results.
        
        Args:
            target_x_cm: Target X position in cm
            target_y_cm: Target Y position in cm
        
        Returns:
            IK calculation result
        """
        self.log(f"\n[IK Test] Testing position: ({target_x_cm:.2f}, {target_y_cm:.2f}) cm")
        
        ik_result = self.inverse_kinematics(target_x_cm, target_y_cm)
        
        if ik_result['success']:
            self.log(f"[IK Test] ✓ SUCCESS")
            self.log(f"[IK Test] X Axis: {ik_result['x_angle_deg']:.2f}° = {ik_result['x_steps']} steps")
            self.log(f"[IK Test] Z Axis: {ik_result['z_angle_deg']:.2f}° = {ik_result['z_steps']} steps")
        else:
            self.log(f"[IK Test] ✗ FAILED: {ik_result['message']}")
        
        return ik_result
    
    def home_axis(self, axis_name, homing_cmd, backoff_cmd):
        """
        Home a single axis.
        
        Args:
            axis_name: Name of axis to home
            homing_cmd: Command to move towards stopper
            backoff_cmd: Command to back off from stopper
        
        Returns:
            str: Status message
        """
        # Clear all commands
        self.X_cmd = ""
        self.Y_cmd = ""
        self.Z_cmd = ""
        self.A_cmd = ""
        
        # Execute homing movement
        if not self.update_axis_command(axis_name, homing_cmd):
            return f"{axis_name} Failed homing - invalid axis name"
        
        # Execute movement using existing method
        result = self.execute_movement(axis_name, homing_cmd)
        
        # Check if stopper was hit
        stopper_status = getattr(self, f"{axis_name}_stopper_status")
        
        if stopper_status:
            self.log(f"[Home] {axis_name} HOMED successfully")
            setattr(self, f"{axis_name}_homing_status", True)
            
            # Back off from stopper
            if self.update_axis_command(axis_name, backoff_cmd):
                self.execute_movement(axis_name, backoff_cmd)
                return f"{axis_name} Homed"
            else:
                return f"{axis_name} Homed (backoff failed)"
        else:
            self.log(f"[Home] {axis_name} FAILED to home - no stopper hit")
            setattr(self, f"{axis_name}_homing_status", False)
            return f"{axis_name} Failed homing"
    
    def sync(self):
        """Perform handshake/sync with robot"""
        if not self.link:
            self.log("[Sync] ERROR: Not connected to robot")
            return False
        
        try:
            self.log("[Sync] Sending handshake...")
            ans = Robot_command("sync", self.link, self.log)
            self.log(f"[Sync] SUCCESS: Robot responded READY = {ans}")
            return True
        except Exception as e:
            self.log(f"[Sync] ERROR: {e}")
            return False
    
    def estop(self):
        """Trigger emergency stop"""
        if not self.link:
            self.log("[E-Stop] ERROR: Not connected to robot")
            return False
        
        try:
            self.log("[E-Stop] Triggering emergency stop...")
            ans = Robot_command("estop", self.link, self.log)
            self.log(f"[E-Stop] Response: {ans}")
            return True
        except Exception as e:
            self.log(f"[E-Stop] ERROR: {e}")
            return False
    
    def clear_estop(self):
        """Clear E-stop and re-enable drivers"""
        if not self.link:
            self.log("[CLR] ERROR: Not connected to robot")
            return False
        
        try:
            self.log("[CLR] Clearing E-stop...")
            resp = Robot_command("clr", self.link, self.log)
            self.log(f"[CLR] Response: {resp}")
            
            # Check if E-stop was cleared successfully
            if "estop_cleared" in resp or "OK" in resp:
                self.log("[CLR] E-stop cleared successfully")
                # Re-enable drivers
                self.log("[CLR] Re-enabling drivers...")
                ena_resp = Robot_command("ena 1", self.link, self.log)
                self.log(f"[CLR] Enable response: {ena_resp}")
                return True
            else:
                self.log("[CLR] Failed to clear E-stop")
                return False
                
        except Exception as e:
            self.log(f"[CLR] ERROR: {e}")
            return False
    
    def set_tech_mode(self, enabled):
        """Enable or disable technician mode (bypasses stopper blocking)"""
        if not self.link:
            self.log("[TECH] ERROR: Not connected to robot")
            return False
        
        try:
            mode = "1" if enabled else "0"
            mode_text = "ENABLED" if enabled else "DISABLED"
            self.log(f"[TECH] Setting technician mode: {mode_text}")
            
            resp = Robot_command(f"tech {mode}", self.link, self.log)
            self.log(f"[TECH] Response: {resp}")
            
            if "OK" in resp or "tech" in resp.lower():
                self.log(f"[TECH] Technician mode {mode_text}")
                if enabled:
                    self.log("[TECH] WARNING: Stopper protection bypassed! Move carefully.")
                return True
            else:
                self.log("[TECH] Failed to set mode")
                return False
                
        except Exception as e:
            self.log(f"[TECH] ERROR: {e}")
            return False
    
    def grip(self, angle):
        """Control gripper servo angle"""
        if not self.link:
            self.log("[Grip] ERROR: Not connected to robot")
            return False
        
        try:
            if angle < 0 or angle > 180:
                self.log(f"[Grip] ERROR: Angle must be 0-180, got {angle}")
                return False
            
            self.log(f"[Grip] Setting gripper to {angle}°")
            resp = Robot_command(f"grip {angle}", self.link, self.log)
            self.log(f"[Grip] Response: {resp}")
            
            if "OK" in resp or "grip" in resp.lower():
                self.log(f"[Grip] Gripper set to {angle}°")
                return True
            else:
                self.log("[Grip] Failed to set gripper angle")
                return False
                
        except Exception as e:
            self.log(f"[Grip] ERROR: {e}")
            return False
    
    def go_to_zero(self):
        """Move robot to zero position - predefined safe position for all axes."""
        if not self.link:
            self.log("[Zero] ERROR: Not connected to robot")
            return False
        
        self.log("[Zero] Setting up zero position commands...")
        
        # Set predefined zero position commands for all axes
        # These values move the robot to a known safe "zero" configuration
        self.update_axis_command('Y', "Y -8000 2000")
        self.update_axis_command('X', "X 3545 2000")
        self.update_axis_command('Z', "Z -4927 2000")
        self.update_axis_command('A', "A -250 500")
        
        self.log("[Zero] Executing zero position movements...")
        self.log("[Y] Mode ACTIVE - Command: Y -8000 2000")
        self.log("[X] Mode ACTIVE - Command: X 3545 2000")
        self.log("[Z] Mode ACTIVE - Command: Z -4927 2000")
        self.log("[A] Mode ACTIVE - Command: A -250 500")
        
        # Execute all movements
        results = self.execute_all_movements()
        
        # Check if all movements completed successfully
        all_success = True
        for axis, result in results.items():
            if not result['success']:
                all_success = False
                self.log(f"[Zero] {axis} axis failed")
            else:
                self.log(f"[Zero] {axis} axis completed")
        
        if all_success and len(results) == 4:
            self.log("[Zero] Successfully moved to zero position")
            
            # Reset all position tracking dictionaries to initial state
            # Last position: Set to (0, 0) at zero position (valid)
            self.last_position['x_cm'] = 0.0
            self.last_position['y_cm'] = 0.0
            self.last_position['x_angle_deg'] = 0.0
            self.last_position['z_angle_deg'] = 0.0
            self.last_position['x_direction'] = 'CW'
            self.last_position['z_direction'] = 'CW'
            self.last_position['distance'] = 0.0
            self.last_position['y_axis_cm'] = -8.0
            self.last_position['is_valid'] = True
            
            # Absolute position: Reset to initial state (invalid/not calculated)
            self.absolute_position['x_cm'] = 0.0
            self.absolute_position['y_cm'] = 0.0
            self.absolute_position['x_angle_deg'] = 0.0
            self.absolute_position['z_angle_deg'] = 0.0
            self.absolute_position['x_direction'] = 'CW'
            self.absolute_position['z_direction'] = 'CW'
            self.absolute_position['distance'] = 0.0
            self.absolute_position['y_axis_cm'] = -8.0
            self.absolute_position['is_valid'] = False
            
            # Secondary absolute position: Reset to initial state (invalid/not calculated)
            self.sec_absolute_position['x_cm'] = 0.0
            self.sec_absolute_position['y_cm'] = 0.0
            self.sec_absolute_position['x_angle_deg'] = 0.0
            self.sec_absolute_position['z_angle_deg'] = 0.0
            self.sec_absolute_position['x_direction'] = 'CW'
            self.sec_absolute_position['z_direction'] = 'CW'
            self.sec_absolute_position['distance'] = 0.0
            self.sec_absolute_position['y_axis_cm'] = -8.0
            self.sec_absolute_position['is_valid'] = False
            
            # Movement angles: Reset to initial state (invalid/not calculated)
            self.movement_angles['x_cm'] = 0.0
            self.movement_angles['y_cm'] = 0.0
            self.movement_angles['x_angle_deg'] = 0.0
            self.movement_angles['z_angle_deg'] = 0.0
            self.movement_angles['x_direction'] = 'CW'
            self.movement_angles['z_direction'] = 'CW'
            self.movement_angles['distance'] = 0.0
            self.movement_angles['y_axis_cm'] = -8.0
            self.movement_angles['is_valid'] = False
            
            # Preferred solution: Reset to initial state (invalid/not calculated)
            self.preferred_solution['x_angle_deg'] = 0.0
            self.preferred_solution['x_direction'] = 'CW'
            self.preferred_solution['z_angle_deg'] = 0.0
            self.preferred_solution['z_direction'] = 'CW'
            self.preferred_solution['distance'] = 0.0
            self.preferred_solution['y_axis_cm'] = -8.0
            self.preferred_solution['is_valid'] = False
            
            self.log("[Zero] All position calculations reset to initial state")
            
            return True
        else:
            self.log("[Zero] Failed to complete all zero movements")
            return False
    
    def pull_up(self):
        """
        Execute PullUP sequence:
        1. Grip to 120 degrees
        2. Wait 2 seconds
        3. Y axis 6 cm down
        4. Wait until end of movement
        5. Grip to 160 degrees
        6. Wait 2 seconds
        7. Y axis 6 cm up
        
        Returns:
            bool: True if sequence completed successfully, False otherwise
        """
        if not self.link:
            self.log("[PullUP] ERROR: Not connected to robot")
            return False
        
        self.log("[PullUP] Starting PullUP sequence...")

        # step 0 : make sure the Z axsis is in the right poisiton for the pull up,
        current_y_axis_cm = self.last_position.get('y_axis_cm', self.last_position.get('Y_axis_cm', 0.0))
        if current_y_axis_cm == 0.0:
            self.update_axis_command('Y', "Y -8000 2000")
            self.log("[Y] Mode ACTIVE - Command: Y -8000 2000")
            # Execute all movements
            results = self.execute_all_movements()
            self.last_position['y_axis_cm'] = -8.0
            self.log("[PullUP] Step 0: Moved Y axis to -8 cm to ensure correct starting position for pull up")
                     
        
        # Step 1: Set grip to 120 degrees
        self.log("[PullUP] Step 1: Setting grip to 120")
        if not self.grip(120):
            self.log("[PullUP] ERROR: Failed to set grip to 120")
            return False
        
        # Step 2: Wait for servo to settle before Y movement
        self.log("[PullUP] Step 2: Waiting 2 seconds for servo to settle...")
        for i in range(20):  # 20 x 0.1s = 2 seconds
            time.sleep(0.1)
            if self.update_callback:
                try:
                    self.update_callback()
                except:
                    pass
        
        # Step 3: Y axis 6 cm down
        # Y axis: 1000 steps per cm, so 6 cm = 6000 steps
        # Down direction = negative
        y_steps_per_cm = self.axis_steps_per_unit.get('Y', 1000)
        y_down_steps = int(-6 * y_steps_per_cm)
        y_speed = self.axis_config['axes']['Y'].get('default_speed', 1000)
        
        self.log(f"[PullUP] Step 3: Moving Y axis 6 cm down ({y_down_steps} steps)")
        y_down_cmd = f"Y {y_down_steps} {y_speed}"
        
        # Execute Y down movement and wait for completion
        result_down = self.execute_movement('Y', y_down_cmd)
        
        # Step 4: Wait until end of movement (already done by execute_movement)
        if not result_down['success']:
            self.log("[PullUP] ERROR: Y axis down movement failed")
            return False
        self.log("[PullUP] Step 4: Y axis down movement complete")
        
        # Step 5: Set grip to 160 degrees
        self.log("[PullUP] Step 5: Setting grip to 160°")
        if not self.grip(160):
            self.log("[PullUP] ERROR: Failed to set grip to 160°")
            return False
        
        # Step 6: Wait 4 seconds for servo to settle
        self.log("[PullUP] Step 6: Waiting 2 seconds for servo to settle...")
        for i in range(20):  # 20 x 0.1s = 2 seconds
            time.sleep(0.1)
            if self.update_callback:
                try:
                    self.update_callback()
                except:
                    pass
        
        # # Additional delay to let servo electrical noise dissipate before Y movement
        # self.log("[PullUP] Step 6b: Extra 3 second delay before Y movement...")
        # for i in range(30):  # 30 x 0.1s = 3 seconds
        #     time.sleep(0.1)
        #     if self.update_callback:
        #         try:
        #             self.update_callback()
        #         except:
        #             pass
        
        # Step 7: Y axis 6 cm up
        y_up_steps = int(6 * y_steps_per_cm)
        self.log(f"[PullUP] Step 7: Moving Y axis 6 cm up ({y_up_steps} steps)")
        y_up_cmd = f"Y {y_up_steps} {y_speed}"
        
        # Execute Y up movement and wait for completion
        result_up = self.execute_movement('Y', y_up_cmd)
        
        if not result_up['success']:
            self.log("[PullUP] ERROR: Y axis up movement failed")
            return False
        
        self.log("[PullUP] ✓ PullUP sequence completed successfully")
        return True
    
    def put_down(self):
        """
        Execute Put Down sequence:
        1. Y axis 6 cm down
        2. Wait until end of movement
        3. Grip to 92 degrees
        4. Wait 2 seconds
        5. Y axis 6 cm up
        
        Returns:
            bool: True if sequence completed successfully, False otherwise
        """
        if not self.link:
            self.log("[PutDown] ERROR: Not connected to robot")
            return False
        
        self.log("[PutDown] Starting Put Down sequence...")
        
        # Step 1: Y axis 6 cm down
        # Y axis: 1000 steps per cm, so 6 cm = 6000 steps
        # Down direction = negative
        y_steps_per_cm = self.axis_steps_per_unit.get('Y', 1000)
        y_down_steps = int(-6 * y_steps_per_cm)
        y_speed = self.axis_config['axes']['Y'].get('default_speed', 1000)
        
        self.log(f"[PutDown] Step 1: Moving Y axis 6 cm down ({y_down_steps} steps)")
        y_down_cmd = f"Y {y_down_steps} {y_speed}"
        
        # Execute Y down movement and wait for completion
        result_down = self.execute_movement('Y', y_down_cmd)
        
        # Step 2: Wait until end of movement (already done by execute_movement)
        if not result_down['success']:
            self.log("[PutDown] ERROR: Y axis down movement failed")
            return False
        self.log("[PutDown] Step 2: Y axis down movement complete")
        
        # Step 3: Set grip to 120 degrees
        self.log("[PutDown] Step 3: Setting grip to 120°")
        if not self.grip(120):
            self.log("[PutDown] ERROR: Failed to set grip to 120°")
            return False
        
        # Step 4: Wait 2 seconds for servo to settle
        self.log("[PutDown] Step 4: Waiting 3 seconds for servo to settle...")
        for i in range(20):  # 20 x 0.1s = 2 seconds
            time.sleep(0.1)
            if self.update_callback:
                try:
                    self.update_callback()
                except:
                    pass
        
        # # Additional delay to let servo electrical noise dissipate before Y movement
        # self.log("[PutDown] Step 4b: Extra 3 second delay before Y movement...")
        # for i in range(30):  # 30 x 0.1s = 3 seconds
        #     time.sleep(0.1)
        #     if self.update_callback:
        #         try:
        #             self.update_callback()
        #         except:
        #             pass
        
        # Step 5: Y axis 6 cm up
        y_up_steps = int(6 * y_steps_per_cm)
        self.log(f"[PutDown] Step 5: Moving Y axis 6 cm up ({y_up_steps} steps)")
        y_up_cmd = f"Y {y_up_steps} {y_speed}"
        
        # Execute Y up movement and wait for completion
        result_up = self.execute_movement('Y', y_up_cmd)
        
        if not result_up['success']:
            self.log("[PutDown] ERROR: Y axis up movement failed")
            return False
        
        self.log("[PutDown] ✓ Put Down sequence completed successfully")
        return True
    
    def cleanup(self):
        """Cleanup and close connections"""
        self.log("[System] Shutting down robot controller...")
        if self.link:
            enable(self.link, False)
            self.link.close()