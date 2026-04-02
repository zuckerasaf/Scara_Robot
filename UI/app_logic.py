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
    
    def reset_remain_limits(self):
        """Reset remain limits to original values from configuration."""
        for axis in ['X', 'Y', 'Z', 'A']:
            self.remain_limits[axis]['min'] = self.axis_limits[axis]['min']
            self.remain_limits[axis]['max'] = self.axis_limits[axis]['max']
        
        self.log("[Limits] Remain limits reset to config values")
    
    def inverse_kinematics(self, target_x_cm, target_y_cm):
        """
        Calculate inverse kinematics for 2-link SCARA arm.
        
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
                'x_angle_deg': float,  # X axis angle in degrees (from vertical)
                'z_angle_deg': float,  # Z axis angle in degrees (from L1)
                'x_angle_direction': str,  # X axis rotation direction ("CW" or "CCW")
                'z_angle_direction': str,  # Z axis rotation direction ("CW" or "CCW")
                'x_steps': int,        # X axis movement in steps
                'z_steps': int,        # Z axis movement in steps
                'message': str         # Status or error message
            }
        """
        # Get robot geometry from config
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
        # calculate shoulder angle (Z axis) using law of cosines
        shoulder_angle_deg =  math.degrees(math.acos((r**2 + L1**2 - L2**2) / (2 * L1 * r)))
        elbow_angle_deg = math.degrees(math.acos((L1**2 + L2**2 - r**2) / (2 * L1 * L2)))
        target_angle_deg = 180 - shoulder_angle_deg - elbow_angle_deg

        shoulder_angle_from_horizontal_deg = math.degrees(math.acos(target_x_cm/r))
        other_shoulder_angle_from_horizontal_deg = 180 - shoulder_angle_from_horizontal_deg - shoulder_angle_deg
        movmet_sholder_angle_deg = 90 - other_shoulder_angle_from_horizontal_deg

        if movmet_sholder_angle_deg < 0:
            movmet_sholder_angle_deg = abs(movmet_sholder_angle_deg)
            shoulder_direction = "CW"  
        else:
            movmet_sholder_angle_deg = abs(movmet_sholder_angle_deg)
            shoulder_direction = "CCW"

        Traget_angle_from_vertical_deg = 90-shoulder_angle_from_horizontal_deg
        other_target_angle_from_vertical_deg = 90 - target_angle_deg-Traget_angle_from_vertical_deg
        movment_elbow_angle_deg = 90 - other_target_angle_from_vertical_deg

        if movment_elbow_angle_deg < 0:
            movment_elbow_angle_deg = abs(movment_elbow_angle_deg)
            elbow_direction = "CW"
        else:
            movment_elbow_angle_deg = abs(movment_elbow_angle_deg)
            elbow_direction = "CW" 



        self.log(f"[IK DEBUG] movment shoulder angle from horizontal: {movmet_sholder_angle_deg:.2f}° ({shoulder_direction}), movement elbow angle: {movment_elbow_angle_deg:.2f}° ({elbow_direction})")

        return {
                'success': True,
                'x_angle_deg': movmet_sholder_angle_deg,
                'z_angle_deg': movment_elbow_angle_deg,
                'x_angle_direction': shoulder_direction,
                'z_angle_direction': elbow_direction,
                'x_steps': 0,
                'z_steps': 0,
                'message': f'IK Success: X={movmet_sholder_angle_deg:.2f}° (from vertical, {shoulder_direction}), Z={movment_elbow_angle_deg:.2f}° (from vertical, {elbow_direction})'
            }
        # # Calculate elbow angle (Z axis) using law of cosines
        # # cos(θ2) = (r² - L1² - L2²) / (-2 * L1 * L2)
        # # This gives the elbow angle. There are two solutions: elbow-up (+) and elbow-down (-)
        # # For SCARA robots, we typically use elbow-down (negative solution)
        # cos_theta2 = (r**2 - L1**2 - L2**2) / (-2 * L1 * L2)
        
        # # Clamp to valid range to avoid math domain errors from floating point precision
        # cos_theta2 = max(-1.0, min(1.0, cos_theta2))
        
        # # Use negative solution for elbow-down configuration
        # theta2_rad = -math.acos(cos_theta2)  # NEGATIVE for elbow-down
        # theta2_deg = math.degrees(theta2_rad)
        
        # # The interior angle between links (beta) = 180° - |theta2|
        # beta_deg = 180.0 - abs(theta2_deg)
        
        # self.log(f"[IK DEBUG] r={r:.2f}cm, cos_theta2={cos_theta2:.4f}")
        # self.log(f"[IK DEBUG] theta2={theta2_deg:.2f}°, beta (interior angle)={beta_deg:.2f}°")
        
        # # Calculate shoulder angle (X axis)
        # # Our coordinate system: +Y points upward/forward, +X points right
        # # Zero position: arms fully extended in +Y direction (0° from vertical)
        # # Standard SCARA formula assumes +Y points down, so we adjust:
        # # θ1 = atan2(y, x) - atan2(L2*sin(θ2), L1 + L2*cos(θ2))
        # # But with Y-up, we need: atan2(-y, x) or adjust the final angle
        
        # # Calculate angle from base to target point
        # angle_to_target = math.atan2(x_base, y_base)  # Note: x,y swapped for "from vertical"
        
        # # Calculate angle offset due to elbow bend
        # # When elbow bends, the shoulder must rotate to compensate
        # k1 = L1 + L2 * math.cos(theta2_rad)
        # k2 = L2 * math.sin(theta2_rad)
        # angle_offset = math.atan2(k2, k1)
        
        # # Shoulder angle from vertical (0° = pointing in +Y direction)
        # theta1_robot_rad = angle_to_target - angle_offset
        # theta1_robot_deg = math.degrees(theta1_robot_rad)
        
        # self.log(f"[IK DEBUG] r={r:.2f}cm, theta2={theta2_deg:.2f}°")
        # self.log(f"[IK DEBUG] angle_to_target={math.degrees(angle_to_target):.2f}°, angle_offset={math.degrees(angle_offset):.2f}°")
        # self.log(f"[IK DEBUG] theta1_robot={theta1_robot_deg:.2f}°")
        
        # # Check angle limits
        # # X axis: ±75° from vertical
        # if abs(theta1_robot_deg) > 75:
        #     return {
        #         'success': False,
        #         'x_angle_deg': theta1_robot_deg,
        #         'z_angle_deg': theta2_deg,
        #         'x_steps': 0,
        #         'z_steps': 0,
        #         'message': f'X axis out of range! Angle: {theta1_robot_deg:.2f}°, Limit: ±75°'
        #     }
        
        # # Z axis: Check motor range limits
        # # At zero position (0,0), geometric angle theta2 ≈ 180° (fully extended)
        # # Motor zero position: -4927 steps = -138° motor position
        # # Motor can move ±140° from zero position
        # theta2_at_zero = 180.0  # Geometric angle at zero position
        # delta_theta2 = theta2_deg - theta2_at_zero  # Change from zero position
        
        # z_motor_range = 140.0  # Motor can move ±140° from zero
        # if abs(delta_theta2) > z_motor_range:
        #     return {
        #         'success': False,
        #         'x_angle_deg': theta1_robot_deg,
        #         'z_angle_deg': theta2_deg,
        #         'x_steps': 0,
        #         'z_steps': 0,
        #         'message': f'Z motor out of range! Needs {delta_theta2:+.2f}° from zero, Limit: ±{z_motor_range}°'
        #     }
        
        # # Convert angles to steps
        # x_steps_per_deg = self.axis_steps_per_unit.get('X', 45.45)
        # z_steps_per_deg = self.axis_steps_per_unit.get('Z', 35.71)
        
        # # X axis: Calculate motor steps relative to zero position
        # # Zero position: 3545 steps corresponds to theta1 = 0° (vertical, pointing down)
        # # CALIBRATION: Direction inverted - multiply by -1
        # x_zero_steps = 3545
        # x_steps = x_zero_steps + int(theta1_robot_deg * x_steps_per_deg) * (-1)
        
        # # Z axis: Calculate motor steps relative to zero position
        # # Zero position: -4927 steps corresponds to theta2 = 180° (fully extended)
        # z_zero_steps = -4927
        # z_steps = z_zero_steps + int(delta_theta2 * z_steps_per_deg)
        
        # self.log(f"[IK DEBUG] Angles: X={theta1_robot_deg:.2f}° (from vertical), Z={theta2_deg:.2f}° (delta={delta_theta2:+.2f}°)")
        # self.log(f"[IK DEBUG] Steps: X={x_steps} (zero+{theta1_robot_deg:.2f}°*{x_steps_per_deg}*-1), Z={z_steps} (zero+{delta_theta2:+.2f}°*{z_steps_per_deg})")
        
        # return {
        #     'success': True,
        #     'x_angle_deg': theta1_robot_deg,
        #     'z_angle_deg': theta2_deg,
        #     'x_steps': x_steps,
        #     'z_steps': z_steps,
        #     'message': f'IK Success: X={theta1_robot_deg:.2f}° (from vertical), Z={theta2_deg:.2f}°'
        # }
    
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
            start_time = time.time()
            
            self.log(f"[Movement] Executing on {axis_name}: {cmd}")
            response = Robot_command(cmd, self.link, self.log)
            
            # Calculate timeout based on movement
            calc_time = abs(int(cmd.split(" ")[1]) / int(cmd.split(" ")[2])) + 1
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
            
            # Query stopper status after movement
            is_pressed = self.query_stopper_status(axis_name)
            setattr(self, f"{axis_name}_stopper_status", is_pressed)
            
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
        
        self.log(f"[IK] Y-axis: {target_y_cm:.2f}cm from zero = {y_steps} steps (zero={y_zero_steps} + {target_y_cm}*{y_steps_per_cm})")
        
        # Use default speeds if not specified
        if speed is None:
            x_speed = self.axis_config['axes']['X'].get('default_speed', 1000)
            y_speed = self.axis_config['axes']['Y'].get('default_speed', 1000)
            z_speed = self.axis_config['axes']['Z'].get('default_speed', 1000)
        else:
            x_speed = y_speed = z_speed = speed
        
        # Create movement commands
        x_cmd = f"X {ik_result['x_steps']} {x_speed}"
        y_cmd = f"Y {y_steps} {y_speed}"
        z_cmd = f"Z {ik_result['z_steps']} {z_speed}"
        
        # Update axis commands
        self.update_axis_command('X', x_cmd)
        self.update_axis_command('Y', y_cmd)
        self.update_axis_command('Z', z_cmd)
        
        # Execute all movements (X, Y, Z will move; A remains empty)
        results = self.execute_all_movements()
        
        # Add results to IK result
        ik_result['movement_results'] = results
        
        return ik_result
    
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
        self.update_axis_command('Y', "Y -8000 1000")
        self.update_axis_command('X', "X 3545 1000")
        self.update_axis_command('Z', "Z -4927 1000")
        self.update_axis_command('A', "A -250 500")
        
        self.log("[Zero] Executing zero position movements...")
        self.log("[Y] Mode ACTIVE - Command: Y -8000 1000")
        self.log("[X] Mode ACTIVE - Command: X 3545 1000")
        self.log("[Z] Mode ACTIVE - Command: Z -4927 1000")
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
            return True
        else:
            self.log("[Zero] Failed to complete all zero movements")
            return False
    
    def cleanup(self):
        """Cleanup and close connections"""
        self.log("[System] Shutting down robot controller...")
        if self.link:
            enable(self.link, False)
            self.link.close()