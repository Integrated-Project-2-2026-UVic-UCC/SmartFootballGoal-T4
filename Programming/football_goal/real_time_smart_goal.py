#source env/bin/activate (open the enviroment)
import cv2
import numpy as np
import time
from collections import deque
from picamera2 import Picamera2

# ==============================
# CONFIGURATION
# ==============================
BALL_DIAMETER_M = 0.22      # Physical size of ball (meters)
TRAJECTORY_BUF = 32         # How many past positions to remember for the path
MIN_RADIUS = 10             # Minimum pixel radius to consider it a ball
ALPHA = 0.4                 # Speed smoothing (0.1 = smooth, 0.9 = instant)

# COLOR SETTINGS (HSV)
LOWER_HSV = np.array([25, 80, 80])
UPPER_HSV = np.array([45, 255, 255])

# ==============================
# INITIALIZE CAMERA
# ==============================
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "RGB888"},
    controls={"FrameDurationLimits": (8333, 8333), "ExposureTime": 3000} 
)
picam2.configure(config)
picam2.start()

# Data storage
pts = deque(maxlen=TRAJECTORY_BUF) # List of (x,y) coordinates
prev_time = None
prev_centroid = None
smoothed_speed_kmh = 0

print("System Active. Press Ctrl+C in terminal to stop.")

try:
    while True:
        # 1. Capture Frame
        frame = picam2.capture_array()
        t_now = time.time()
        
        # 2. Image Processing (Color Detection)
        # Picamera2 returns RGB, OpenCV usually uses HSV for color masking
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)
        mask = cv2.inRange(hsv, LOWER_HSV, UPPER_HSV)
        
        # Clean up noise (remove small dots, smooth edges)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)

        # 3. Find Ball Contours
        cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center = None

        if len(cnts) > 0:
            # Find the largest contour (the ball)
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            M = cv2.moments(c)
            
            # Calculate Center
            if M["m00"] > 0:
                center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

            # Only process if it meets a minimum size
            if radius > MIN_RADIUS:
                # --- VISUALS: Draw ball outline ---
                cv2.circle(frame, (int(x), int(y)), int(radius), (0, 255, 255), 2)
                cv2.circle(frame, center, 5, (0, 0, 255), -1)

                # --- SPEED CALCULATION ---
                if prev_centroid is not None and prev_time is not None:
                    dt = t_now - prev_time
                    if 0 < dt < 0.2: # Only calc if detection is continuous
                        # Calculate pixel movement
                        dx = center[0] - prev_centroid[0]
                        dy = center[1] - prev_centroid[1]
                        dist_px = np.hypot(dx, dy)

                        # Dynamic Calibration: 
                        # Ratio = Real Diameter / Pixel Diameter
                        m_per_px = BALL_DIAMETER_M / (2 * radius)
                        dist_m = dist_px * m_per_px
                        
                        # Calculate Speed
                        speed_mps = dist_m / dt
                        current_kmh = speed_mps * 3.6
                        
                        # Apply smoothing filter
                        smoothed_speed_kmh = (ALPHA * current_kmh) + (1 - ALPHA) * smoothed_speed_kmh

                prev_centroid = center
                prev_time = t_now
        else:
            # If ball is lost, reset tracking history to avoid speed spikes
            prev_centroid = None
            prev_time = None

        # 4. Trajectory Tracking (The "Tail")
        pts.appendleft(center)

        # Draw the trajectory line
        for i in range(1, len(pts)):
            if pts[i - 1] is None or pts[i] is None:
                continue
            
            # Thickness gets smaller for older points (visual effect), not needed but i wanted to do it
            thickness = int(np.sqrt(TRAJECTORY_BUF / float(i + 1)) * 2.5)
            cv2.line(frame, pts[i - 1], pts[i], (0, 255, 0), thickness)

        # 5. UI Overlays
        cv2.putText(frame, f"Speed: {smoothed_speed_kmh:.1f} km/h", (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        
        # Display the result
        cv2.imshow("Smart Football Tracker", frame)

        # Exit on 'q'
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
