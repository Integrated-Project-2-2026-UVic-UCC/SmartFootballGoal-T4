"""
sources.py
──────────
Unified frame-source interface.

Both sources expose the same two methods:
    read()    → (ok: bool, frame: np.ndarray)
    release() → None

Switch between them via config.MODE.
"""

import cv2
import config  

# ── Live camera (PiCamera2) ───────────────────────────────────────────────────

class CameraSource:
    def __init__(self, cfg):
        from picamera2 import Picamera2          # imported here so the rest of the
                                                 # codebase works without picamera2
        self._cam = Picamera2()
        cam_cfg = self._cam.create_video_configuration(
            main={"size": (cfg.IMG_W, cfg.IMG_H), "format": "BGR888"},
            controls={
                "FrameDurationLimits": (cfg.FRAME_DURATION, cfg.FRAME_DURATION),
                "ExposureTime":        cfg.EXPOSURE_TIME,
            },
        )
        self._cam.configure(cam_cfg)
        self._cam.start()

    def read(self):
        return True, self._cam.capture_array()

    def release(self):
        self._cam.stop()



# ── Factory ───────────────────────────────────────────────────────────────────

def build_source(cfg):
    """Return the appropriate source based on cfg.MODE."""
    return CameraSource(cfg)
    