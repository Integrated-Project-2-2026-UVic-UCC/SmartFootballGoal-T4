"""
drawing.py
──────────
All OpenCV annotation helpers.
"""

import cv2
import config  

def draw_ball(frame, x_px: float, y_px: float, radius: float,
              z_m: float, velocity: float) -> None:
    """Overlay circle, depth label and velocity on *frame* in-place."""
    cx, cy, r = int(x_px), int(y_px), int(radius)

    # Detection circle
    cv2.circle(frame, (cx, cy), r, (0, 255, 0), 2)

    # Depth tag above the ball
    cv2.putText(frame, f"Z: {z_m:.2f} m",
                (cx, cy - 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

    # Velocity (top-left corner)
    cv2.putText(frame, f"Vel: {velocity:.2f} m/s",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)


def draw_mode_label(frame, mode: str) -> None:
    """Small mode indicator in the top-right corner."""
    label = f"MODE: {mode.upper()}"
    cv2.putText(frame, label,
                (frame.shape[1] - 180, 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
