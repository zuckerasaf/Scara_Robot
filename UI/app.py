"""
SCARA Robot Controller - Main Application Entry Point

This is the main entry point that connects the UI and logic layers.
"""

import tkinter as tk
import sys
import os

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from serial_link import SerialLink
from motions import handshake, enable
from app_logic import RobotController
from app_ui import ScaraMainWindow

PORT = "COM3"
BAUD = 115200


def main():
    """Main entry point for the application."""
    # Try to connect to the robot
    link = None
    try:
        link = SerialLink(PORT, BAUD)
        link.open()
        if handshake(link):
            print("Handshake successful - robot connected")
            enable(link, True)
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
    
    # Create Tkinter root
    root = tk.Tk()
    
    # Create robot controller (business logic)
    robot_controller = RobotController(serial_link=link)
    
    # Create main window (UI)
    app = ScaraMainWindow(root, robot_controller)
    
    # Set robot controller's log callback to UI's log method
    robot_controller.log = app.log
    
    # Set update callback to keep UI responsive during movements
    robot_controller.update_callback = root.update
    
    # Cleanup on exit
    def on_closing():
        app.on_exit()
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()