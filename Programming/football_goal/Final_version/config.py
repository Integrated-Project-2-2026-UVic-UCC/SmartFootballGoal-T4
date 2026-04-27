import math

# ─────────────────────────────────────────────
#  MODE SWITCH  →  "camera"  |  "video"
# ─────────────────────────────────────────────
MODE       = "camera"
VIDEO_PATH = "video.mp4"   # used only when MODE == "video"

# ── Ball & optics ────────────────────────────
BALL_DIAMETER_M    = 0.204
CALIBRATION_FACTOR = 2.14
H_FOV              = 62.2       # horizontal field-of-view in degrees
IMG_W, IMG_H       = 640, 480
MIN_RADIUS         = 6          # px — smaller detections are ignored

# ── Derived constants (do not edit) ──────────
CX, CY          = IMG_W // 2, IMG_H // 2
TAN_FOV_2       = math.tan(math.radians(H_FOV / 2))
FOCAL_LENGTH_PX = IMG_W / (2 * TAN_FOV_2)

# ── HSV colour range for the ball ────────────
HSV_LOWER = (108, 134, 121)
HSV_UPPER = (121, 255, 255)

# ── Velocity smoothing & noise filter ────────
VELOCITY_ALPHA     = 0.7   # weight of the previous smoothed value (0–1)
VELOCITY_THRESHOLD = 0.5   # m/s — values below this are shown as 0

# ── PiCamera2 settings (camera mode only) ────
FRAME_DURATION = 11_111    # µs  (~90 fps cap)
EXPOSURE_TIME  = 2_000     # µs
