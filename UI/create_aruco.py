import cv2
import os

# Create output folder
output_dir = r"C:\projectPython\Scara_Robot\arcuo_png"
os.makedirs(output_dir, exist_ok=True)

# Choose dictionary
aruco_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_50)

# Marker settings
marker_size = 150  # pixels
marker_ids = [5]

for marker_id in marker_ids:
    marker_img = cv2.aruco.generateImageMarker(aruco_dict, marker_id, marker_size)
    filename = os.path.join(output_dir, f"marker_{marker_id}.png")
    cv2.imwrite(filename, marker_img)
    print(f"Saved {filename}")