import cv2
import numpy as np
import time
import math
from picamera2 import Picamera2

# --- CONFIGURATION ---
BALL_DIAMETER_M = 0.204 
# This factor is based on a test (Actual_Dist / Measured_Dist)
CALIBRATION_FACTOR = 2.14 

H_FOV = 62.2
IMG_W, IMG_H = 640, 480
CX, CY = IMG_W // 2, IMG_H // 2

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (IMG_W, IMG_H), "format": "BGR888"},
    controls={"FrameDurationLimits": (11111, 11111), "ExposureTime": 2000}
)
picam2.configure(config)
picam2.start()

# Pre-calculate part of the distance formula
TAN_FOV_2 = math.tan(math.radians(H_FOV / 2))

try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        # Color masking (using your previous values)
        mask = cv2.inRange(hsv, np.array([108, 124, 56]), np.array([156, 223, 207]))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            pixel_diameter = 2 * radius

            if radius > 4:
                # 1. Calculate Plane of View
                plane_of_view = (BALL_DIAMETER_M * IMG_W) / pixel_diameter
                
                # 2. Calculate Z and apply Calibration Factor
                z_m_raw = (plane_of_view / TAN_FOV_2) / 2
                z_m = z_m_raw * CALIBRATION_FACTOR 
                
                # Screen Drawing
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
                cv2.putText(frame, f"Dist: {z_m:.2f}m", (int(x), int(y) - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)

        cv2.imshow("Calibration Mode", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    picam2.stop()
    cv2.destroyAllWindows()