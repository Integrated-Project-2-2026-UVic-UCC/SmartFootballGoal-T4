import cv2
import numpy as np
from collections import deque
import os

# ==============================
# CONFIGURATION
# ==============================
VIDEO_PATH = "Football_ball.mp4"
BALL_DIAMETER_M = 0.22      # Size 5 ball (meters)
TRAJECTORY_BUF = 20
ALPHA = 0.3                 # Smoothing factor

# --- FOCAL LENGTH ESTIMATION ---
# For a standard 720p/1080p webcam, 700-800 is a good estimate.
# If the speed seems too high, increase this. If too low, decrease it.
FOCAL_LENGTH_PX = 750       

# HSV for White/Light ball
LOWER_WHITE = np.array([0, 0, 160])   
UPPER_WHITE = np.array([180, 60, 255])

# ==============================
# INITIALIZATION
# ==============================
cap = cv2.VideoCapture(VIDEO_PATH)
fps = cap.get(cv2.CAP_PROP_FPS)
if fps <= 0: fps = 30.0
dt = 1.0 / fps

# History tracking
pts = deque(maxlen=TRAJECTORY_BUF)
prev_data = None # Will store (x, y, z)
smoothed_speed_kmh = 0

cv2.namedWindow("3D Smart Goal Analysis", cv2.WINDOW_NORMAL)

# ==============================
# MAIN LOOP
# ==============================
while cap.isOpened():
    ret, frame = cap.read()
    if not ret: break

    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, LOWER_WHITE, UPPER_WHITE)
    mask = cv2.GaussianBlur(mask, (5, 5), 0)
    mask = cv2.dilate(mask, None, iterations=2)
    mask = cv2.erode(mask, None, iterations=1)

    cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    center = None

    if len(cnts) > 0:
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        pixel_diameter = 2 * radius
        
        
        if radius > 8:
            center = (int(x), int(y))
            
            # 1. CALCULATE 3D POSITION (X, Y, Z)
            # Distance from camera (Z) based on size
            z_m = (BALL_DIAMETER_M * FOCAL_LENGTH_PX) / pixel_diameter
            
            # Real-world X and Y (converting pixels to meters at that specific Z distance)
            m_per_px = BALL_DIAMETER_M / pixel_diameter
            x_m = x * m_per_px
            y_m = y * m_per_px

            # 2. CALCULATE 3D VELOCITY
            if prev_data is not None:
                # Changes in distance (meters)
                dx = x_m - prev_data['x']
                dy = y_m - prev_data['y']
                dz = z_m - prev_data['z'] # Rate of approach (The "Growth")

                # 3D Pythagorean Theorem
                dist_3d = np.sqrt(dx**2 + dy**2 + dz**2)
                
                speed_mps = dist_3d / dt
                current_kmh = speed_mps * 3.6
                
                if current_kmh < 250: # Ignore noise spikes
                    smoothed_speed_kmh = (ALPHA * current_kmh) + (1 - ALPHA) * smoothed_speed_kmh

            # Store current data for next frame comparison
            prev_data = {'x': x_m, 'y': y_m, 'z': z_m}

            # Visuals
            cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 0), 2)
            # Show distance from camera
            cv2.putText(frame, f"Dist: {z_m:.1f}m", (int(x)+10, int(y)), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1)
    else:
        prev_data = None

    # 3. Trajectory & UI
    pts.appendleft(center)
    for i in range(1, len(pts)):
        if pts[i-1] is None or pts[i] is None: continue
        cv2.line(frame, pts[i-1], pts[i], (0, 0, 255), 2)

    # UI Panel
    cv2.rectangle(frame, (10, 10), (350, 65), (0, 0, 0), -1)
    cv2.putText(frame, f"TOTAL SPEED: {smoothed_speed_kmh:.1f} km/h", (20, 45),
                cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
    
    cv2.imshow("3D Smart Goal Analysis", frame)

    key = cv2.waitKey(int(dt * 1000)) & 0xFF 
    if key == ord('q'): break
    if key == ord('p'): cv2.waitKey(-1)

cap.release()
cv2.destroyAllWindows()