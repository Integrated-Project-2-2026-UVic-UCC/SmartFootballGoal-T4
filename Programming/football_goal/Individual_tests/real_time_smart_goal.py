import cv2
import numpy as np
import time
import math
from picamera2 import Picamera2

# --- CONFIGURATION ---
BALL_DIAMETER_M = 0.204 
CALIBRATION_FACTOR = 2.14 
H_FOV = 62.2
IMG_W, IMG_H = 640, 480
CX, CY = IMG_W // 2, IMG_H // 2

# Calculate Focal Length in pixels once
FOCAL_LENGTH_PX = IMG_W / (2 * math.tan(math.radians(H_FOV / 2)))

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (IMG_W, IMG_H), "format": "BGR888"},
    controls={"FrameDurationLimits": (11111, 11111), "ExposureTime": 2000}
)
picam2.configure(config)
picam2.start()

# --- TRACKING VARIABLES ---
prev_time = None
prev_x_m = None
prev_y_m = None
prev_z_m = None
velocity = 0.0
show_vel = 0.0

TAN_FOV_2 = math.tan(math.radians(H_FOV / 2))

try:
    while True:
        frame = picam2.capture_array()
        current_time = time.time()
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        
        mask = cv2.inRange(hsv, np.array([108, 134, 121]), np.array([121, 255, 255]))
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            ((x_px, y_px), radius) = cv2.minEnclosingCircle(c)
            pixel_diameter = 2 * radius

            if radius > 6:
                # 1. Calculate Z (Depth)
                plane_of_view = (BALL_DIAMETER_M * IMG_W) / pixel_diameter
                z_m_raw = (plane_of_view / TAN_FOV_2) / 2
                z_m = z_m_raw * CALIBRATION_FACTOR 
                
                # 2. Calculate Real-World X and Y (in meters)
                # Formula: World_X = (Pixel_X - Center_X) * Z / Focal_Length
                x_m = (x_px - CX) * (z_m / FOCAL_LENGTH_PX)
                y_m = (y_px - CY) * (z_m / FOCAL_LENGTH_PX)

                # 3. Calculate Velocity
                if prev_time is not None:
                    dt = current_time - prev_time
                    if dt > 0:
                        # Calculate displacement for each axis
                        dx = x_m - prev_x_m
                        dy = y_m - prev_y_m
                        dz = z_m - prev_z_m
                        
                        # Total 3D distance moved (Euclidean distance)
                        dist_moved = math.sqrt(dx**2 + dy**2 + dz**2)
                        
                        # Velocity = Distance / Time
                        # Note: We use a simple smoothing to avoid "jittery" numbers
                        instant_velocity = dist_moved / dt 
                        velocity = (velocity * 0.7) + (instant_velocity * 0.3) #Stardard incrementation
                        if velocity <= 1:
                            show_vel = 0.0
                        else:
                            show_vel = velocity

                # Update previous values for next frame
                prev_x_m, prev_y_m, prev_z_m = x_m, y_m, z_m
                prev_time = current_time

                # --- DRAWING ---
                cv2.circle(frame, (int(x_px), int(y_px)), int(radius), (0, 255, 0), 2)
                cv2.putText(frame, f"Z: {z_m:.2f}m", (int(x_px), int(y_px) - 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)
                cv2.putText(frame, f"Vel: {show_vel:.2f} m/s", (20, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
        else:
            # Reset tracking if ball is lost
            prev_time = None

        cv2.imshow("Velocity Tracking", frame)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
finally:
    picam2.stop()
    cv2.destroyAllWindows()
