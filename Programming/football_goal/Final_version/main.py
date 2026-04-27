"""
main.py
───────
Entry point.  Change config.MODE to switch between live camera and video file.

    config.MODE = "camera"          → PiCamera2 real-time stream
    config.MODE = "video"           → video file at config.VIDEO_PATH

Press  Q  to quit at any time.
"""

import time
import cv2

import config
import server                               # ← web server                  
from sources   import build_source
from detection import detect_ball
from tracker   import BallTracker
from drawing   import draw_ball, draw_mode_label

# Distance window that triggers a server push (meters)
_ZONE_NEAR     = 0.05                       #     0.295                          
_ZONE_FAR      = 2.305                       #          0.305                     
_SEND_INTERVAL = 2.0                        # seconds between pushes        


def run_loop(source, tracker: BallTracker, mode: str) -> None:
    """Main capture-detect-track-draw loop."""
    last_send_time = 0.0                    

    try:
        while True:
            ok, frame = source.read()
            if not ok:                         # video ended / camera error
                break

            current_time = time.time()
            detection = detect_ball(frame, config.HSV_LOWER, config.HSV_UPPER, config.MIN_RADIUS)

            if detection:
                x_px, y_px, radius = detection
                result = tracker.update(x_px, y_px, radius, current_time)
                draw_ball(frame, x_px, y_px, radius,
                          result["z_m"], result["velocity"])

                # ── Push to web server every 2 s when inside target zone ──
                in_zone  = _ZONE_NEAR <= result["z_m"] <= _ZONE_FAR
                time_due = (current_time - last_send_time) >= _SEND_INTERVAL
                if in_zone and time_due:
                    server.record_velocity(result["velocity"], result["z_m"])
                    last_send_time = current_time
                # ─────────────────────────────────────────────────────────
            else:
                tracker.reset()

            draw_mode_label(frame, mode)

            cv2.imshow("Ball Velocity Tracker", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        source.release()
        cv2.destroyAllWindows()


def main():
    print(f"[INFO] Starting in '{config.MODE}' mode.")

    server.start()                          # launch Flask in background     [NEW]

    source  = build_source(config)
    tracker = BallTracker(config)

    run_loop(source, tracker, config.MODE)

    print("[INFO] Tracker stopped.")


if __name__ == "__main__":
    main()
