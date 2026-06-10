"""
main.py
───────
Entry point.  Run with:  python main.py

Works with or without a display (headless):
  - With HDMI: shows a real-time OpenCV (cv2) window.
  - Without HDMI: skips the entire UI; tracking and recording work exactly the same.

Goal clip recording is triggered when ALL three conditions are true:
  1. Ball is inside the goal zone      (GOAL_ZONE_NEAR ≤ z ≤ GOAL_ZONE_FAR)
  2. Ball velocity exceeds minimum     (velocity > GOAL_MIN_VELOCITY)
  3. Cooldown has elapsed              (≥ GOAL_SEND_INTERVAL s since last trigger)

Press Q to quit (display mode only).
"""

import atexit
import os
import time
import cv2

import config
import server
import hotspot
import recording
from sources   import build_source
from detection import detect_ball
from tracker   import BallTracker
from drawing   import draw_ball


def _has_display() -> bool:
  """Returns True if a display server is available."""
  # On a headless Linux system (e.g., a Raspberry Pi without HDMI),
  # DISPLAY and WAYLAND_DISPLAY will be unset. We check both before
  # attempting to use OpenCV.
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
       # Secondary check: verify that OpenCV can actually create a window.
        try:
            cv2.namedWindow("__test__", cv2.WINDOW_NORMAL)
            cv2.destroyWindow("__test__")
            return True
        except Exception:
            return False
    return False


def run_loop(source, tracker: BallTracker, recorder: recording.GoalRecorder,
             headless: bool) -> None:
    last_trigger_time = 0.0

    if headless:
        print("[INFO] Headless mode — no screen to see the process.")

    try:
        while True:
            ok, frame = source.read()
            if not ok:
                break

            current_time = time.time()
            detection    = detect_ball(
                frame, config.HSV_LOWER, config.HSV_UPPER, config.MIN_RADIUS
            )

            if detection:
                x_px, y_px, radius = detection
                result = tracker.update(x_px, y_px, radius, current_time)

                # ── Goal detection and recording trigger ────────────────────
                in_zone     = config.GOAL_ZONE_NEAR <= result["z_m"] <= config.GOAL_ZONE_FAR
                fast_enough = result["velocity"] > config.GOAL_MIN_VELOCITY
                cooldown_ok = (current_time - last_trigger_time) >= config.GOAL_SEND_INTERVAL

                if in_zone and fast_enough and cooldown_ok:
                    server.record_velocity(result["velocity"], result["z_m"])
                    recorder.trigger_goal(current_time, result["velocity"], result["z_m"])
                    last_trigger_time = current_time
                # ─────────────────────────────────────────────────────────

                if not headless:
                    draw_ball(frame, x_px, y_px, radius, result["z_m"], result["velocity"])

            else:
                tracker.reset()

            # Feed the annotated frame into the rolling buffer every frame
            # In headless the frame dosn't have anotations 
            #---------------------------------------
            recorder.add_frame(frame, current_time)

            if not headless:
                cv2.imshow("Ball Velocity Tracker", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
            else:
                # Without a display: yield CPU time to the OS so the recording and server
                # threads can continue running.
                # 10 ms is sufficient at 90 FPS (the main loop takes ~11 ms per frame).
                time.sleep(0.010)

    finally:
        source.release()
        if not headless:
            cv2.destroyAllWindows()


def main():
    print("[INFO] Starting ball tracker.")

    # ── 1. Bring up the WiFi hotspot ─────────────────────────────────────────
    info = hotspot.start()
    atexit.register(hotspot.stop)

    # ── 2. Tell the web server about the hotspot ──────────────────────────────
    server.set_hotspot_info(
        ssid     = info["ssid"],
        password = info["password"],
        url      = info["url"],
    )

    # ── 3. Start the Flask server ─────────────────────────────────────────────
    server.start()

    # ── 4. Detect display availability ───────────────────────────────────────
    headless = not _has_display()

    # ── 5. Start tracker and recorder ────────────────────────────────────────
    source   = build_source(config)
    tracker  = BallTracker(config)
    recorder = recording.GoalRecorder(server, config)

    run_loop(source, tracker, recorder, headless)

    print("[INFO] Tracker stopped.")


if __name__ == "__main__":
    main()
