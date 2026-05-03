import math

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

# ── PiCamera2 settings ───────────────────────
FRAME_DURATION = 11_111    # µs  (~90 fps cap)
EXPOSURE_TIME  = 2_000     # µs

# ── Goal detection & server push ─────────────
GOAL_ZONE_NEAR     = 0.105  # m — near edge of goal zone
GOAL_ZONE_FAR      = 1.005  # m — far  edge of goal zone
GOAL_SEND_INTERVAL = 5.0   # s  — minimum time between server pushes
GOAL_MIN_VELOCITY  = 1.0  # m/s — shots below this speed are ignored

# ── Recording ────────────────────────────────
VIDEO_DIR          = "videos"   # folder where goal clips are saved
PRE_TRIGGER_S      = 1.0        # seconds of footage to keep before the goal
POST_TRIGGER_S     = 1.0        # seconds of footage to capture after the goal
BUFFER_MAX_AGE_S   = 5.0        # rolling buffer depth (seconds)
SLOWMO_FACTOR      = 4          # 4 → video plays at ¼ real speed
