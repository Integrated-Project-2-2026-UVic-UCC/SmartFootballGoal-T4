"""
detection.py
────────────
Finds the ball in a single BGR frame using HSV colour thresholding.
Returns None if nothing is detected, or (x_px, y_px, radius) otherwise.
"""

import cv2
import numpy as np
import config

def detect_ball(frame, hsv_lower, hsv_upper, min_radius: float):
    """
    Detect the largest circular blob inside the HSV colour range.

    Returns:
        (x_px, y_px, radius)   floats, centre and radius in pixels
        None                   if no valid detection
    """
    hsv  = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(hsv_lower), np.array(hsv_upper))

    cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not cnts:
        return None

    largest = max(cnts, key=cv2.contourArea)
    (x_px, y_px), radius = cv2.minEnclosingCircle(largest)

    if radius <= min_radius:
        return None

    return x_px, y_px, radius
