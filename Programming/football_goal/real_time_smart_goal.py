import cv2
import numpy as np
import time
import math
from collections import deque
from picamera2 import Picamera2

BALL_DIAMETER_M = 0.21
H_FOV = 62.2
TRAJECTORY_BUF = 20
ALPHA = 0.3

# HSV Colors
LOWER_COLOR = np.array([108, 124, 56])
UPPER_COLOR = np.array([156, 223, 207])  # with the filter

picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "BGR888"},
    controls={
        "FrameDurationLimits": (11111, 11111),
        "ExposureTime": 2000
    }
)

picam2.configure(config)
picam2.start()

IMG_W, IMG_H = 640, 480
CX, CY = IMG_W // 2, IMG_H // 2

# Focal length exact
FOCAL_L = (IMG_W / 2) / math.tan(math.radians(H_FOV / 2))

pts = deque(maxlen=TRAJECTORY_BUF)
prev_data = None
prev_time = time.time()
smoothed_speed_kmh = 0

print(f"Going in 90 FPS. Focal Length: {FOCAL_L:.2f}")

try:
    while True:
        # 1. Image taking
        frame = picam2.capture_array()
        t_now = time.time()

        # 2. Processing the image
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # 3. Color masking
        mask = cv2.inRange(hsv, LOWER_COLOR, UPPER_COLOR)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)
        mask = cv2.dilate(mask, None, iterations=2)
        mask = cv2.erode(mask, None, iterations=1)

        # DEBUG
        cv2.imshow("Mascara", mask)

        cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center_px = None

        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            ((x, y), radius) = cv2.minEnclosingCircle(c)
            pixel_diameter = 2 * radius

            if radius > 4:
                center_px = (int(x), int(y))

                # --- POSITION 3D ---
                z_m = (BALL_DIAMETER_M * FOCAL_L) / pixel_diameter
                m_per_px = BALL_DIAMETER_M / pixel_diameter
                x_m = (x - CX) * m_per_px
                y_m = (y - CY) * m_per_px

                # --- SPEED ---
                dt = t_now - prev_time
                if prev_data is not None and dt > 0:
                    dx = x_m - prev_data['x']
                    dy = y_m - prev_data['y']
                    dz = z_m - prev_data['z']

                    dist_3d = math.sqrt(dx**2 + dy**2 + dz**2)
                    speed_mps = dist_3d / dt
                    current_kmh = speed_mps * 3.6

                    if current_kmh < 250:
                        smoothed_speed_kmh = (
                            ALPHA * current_kmh +
                            (1 - ALPHA) * smoothed_speed_kmh
                        )

                prev_data = {'x': x_m, 'y': y_m, 'z': z_m}
                prev_time = t_now

                # Screen Drowing
                cv2.circle(frame, center_px, int(radius), (0, 255, 0), 2)
                cv2.putText(
                    frame,
                    f"{z_m:.1f}m",
                    (center_px[0] + 10, center_px[1]),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (255, 255, 0),
                    1
                )
        else:
            prev_data = None
            prev_time = t_now

        # UI
        cv2.rectangle(frame, (10, 10), (320, 60), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"Vel: {smoothed_speed_kmh:.1f} km/h",
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )

        cv2.imshow("Smart Goal 3D", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
