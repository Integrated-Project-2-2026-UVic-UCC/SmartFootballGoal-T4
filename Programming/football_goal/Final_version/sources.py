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


# ── Pre-recorded video file ───────────────────────────────────────────────────

class VideoSource:
    def __init__(self, path: str):
        self._cap = cv2.VideoCapture(path)
        if not self._cap.isOpened():
            raise FileNotFoundError(f"Cannot open video file: '{path}'")

    def read(self):
        return self._cap.read()          # (ret, frame) – standard OpenCV tuple

    def release(self):
        self._cap.release()


# ── Factory ───────────────────────────────────────────────────────────────────

def build_source(cfg):
    """Return the appropriate source based on cfg.MODE."""
    if cfg.MODE == "camera":
        return CameraSource(cfg)
    elif cfg.MODE == "video":
        return VideoSource(cfg.VIDEO_PATH)
    else:
        raise ValueError(f"Unknown MODE '{cfg.MODE}'. Use 'camera' or 'video'.")
