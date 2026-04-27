"""
tracker.py
──────────
Stateful tracker that converts a pixel detection into a 3-D world position
and computes a smoothed velocity across consecutive frames.
"""

import math
import config

class BallTracker:
    def __init__(self, cfg):
        self.cfg = cfg
        self._reset_state()

    # ── Public API ────────────────────────────────────────────────────────────

    def update(self, x_px: float, y_px: float, radius: float, timestamp: float):
        """
        Process a new detection and update velocity.

        Args:
            x_px, y_px : ball centre in pixels
            radius      : ball radius in pixels
            timestamp   : time.time() value for the current frame

        Returns:
            dict with keys: x_m, y_m, z_m, velocity
        """
        pos = self._pixel_to_world(x_px, y_px, radius)
        self._update_velocity(pos, timestamp)

        self._prev_pos  = pos
        self._prev_time = timestamp

        return {"x_m": pos[0], "y_m": pos[1], "z_m": pos[2],
                "velocity": self.show_vel}

    def reset(self):
        """
        Call when the ball is lost between frames.
        This resets the velocity and prevents a large jump when the ball is detected again.
        But this might cause some errors so posible changes could be to only reset the velocity and not the position, or to keep the last position for a few frames before resetting it.
        """
        self._reset_state()

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _reset_state(self):
        self._prev_time = None
        self._prev_pos  = None      # (x_m, y_m, z_m)
        self.velocity   = 0.0      # smoothed velocity  (m/s)
        self.show_vel   = 0.0      # displayed velocity (m/s)

    def _pixel_to_world(self, x_px, y_px, radius):
        """Convert pixel detection to real-world (x, y, z) in metres."""
        cfg = self.cfg
        pixel_diameter = 2 * radius

        # Depth (Z) via angular size of the known-diameter ball
        plane_width = (cfg.BALL_DIAMETER_M * cfg.IMG_W) / pixel_diameter
        z_m = (plane_width / cfg.TAN_FOV_2 / 2) * cfg.CALIBRATION_FACTOR

        # Lateral position using the pin-hole camera model
        x_m = (x_px - cfg.CX) * (z_m / cfg.FOCAL_LENGTH_PX)
        y_m = (y_px - cfg.CY) * (z_m / cfg.FOCAL_LENGTH_PX)

        return x_m, y_m, z_m

    def _update_velocity(self, current_pos, current_time):
        """Exponential smoothing over the 3-D Euclidean displacement."""
        if self._prev_time is None or self._prev_pos is None:
            return

        dt = current_time - self._prev_time
        if dt <= 0:
            return

        dx, dy, dz = (current_pos[i] - self._prev_pos[i] for i in range(3))
        instant_vel = math.sqrt(dx**2 + dy**2 + dz**2) / dt

        alpha = self.cfg.VELOCITY_ALPHA
        self.velocity = alpha * self.velocity + (1 - alpha) * instant_vel
        self.show_vel = (0.0 if self.velocity <= self.cfg.VELOCITY_THRESHOLD
                         else self.velocity)
