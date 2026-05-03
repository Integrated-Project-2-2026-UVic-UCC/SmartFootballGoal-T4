"""
main.py
───────
Entry point.  Run with:  python main.py

Goal clip recording is triggered when ALL three conditions are true:
  1. Ball is inside the goal zone   (GOAL_ZONE_NEAR ≤ z ≤ GOAL_ZONE_FAR)
  2. Ball velocity exceeds minimum  (velocity > GOAL_MIN_VELOCITY)
  3. Cooldown has elapsed           (≥ GOAL_SEND_INTERVAL s since last trigger)

WiFi hotspot
────────────
  On startup the app creates its own WiFi hotspot (SmartGoal / football1 by default).
  Other devices join that network and open the URL shown in the terminal.
  Override SSID / password via environment variables before running:
      HOTSPOT_SSID=MyGoal HOTSPOT_PASSWORD=secret123 python main.py

Press  Q  to quit.
"""

import atexit
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


def run_loop(source, tracker: BallTracker, recorder: recording.GoalRecorder) -> None:
    last_trigger_time = 0.0

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

                draw_ball(frame, x_px, y_px, radius, result["z_m"], result["velocity"])

                # ── Goal detection & recording trigger ────────────────────
                in_zone     = config.GOAL_ZONE_NEAR <= result["z_m"] <= config.GOAL_ZONE_FAR
                fast_enough = result["velocity"] > config.GOAL_MIN_VELOCITY
                cooldown_ok = (current_time - last_trigger_time) >= config.GOAL_SEND_INTERVAL

                if in_zone and fast_enough and cooldown_ok:
                    server.record_velocity(result["velocity"], result["z_m"])
                    recorder.trigger_goal(current_time, result["velocity"], result["z_m"])
                    last_trigger_time = current_time
                # ─────────────────────────────────────────────────────────

            else:
                tracker.reset()

            
            # Feed the annotated frame into the rolling buffer every frame
            recorder.add_frame(frame, current_time)

            cv2.imshow("Ball Velocity Tracker", frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    finally:
        source.release()
        cv2.destroyAllWindows()


def main():
    print("[INFO] Starting ball tracker.")

    # ── 1. Bring up the WiFi hotspot ─────────────────────────────────────────
    info = hotspot.start()
    atexit.register(hotspot.stop)   # clean up on exit

    # ── 2. Tell the web server about the hotspot so the dashboard can show it ─
    server.set_hotspot_info(
        ssid     = info["ssid"],
        password = info["password"],
        url      = info["url"],
    )

    # ── 3. Start the Flask server ─────────────────────────────────────────────
    server.start()

    # ── 4. Start tracker and recorder ────────────────────────────────────────
    source   = build_source(config)
    tracker  = BallTracker(config)
    recorder = recording.GoalRecorder(server, config)

    run_loop(source, tracker, recorder)

    print("[INFO] Tracker stopped.")


if __name__ == "__main__":
    main()
