"""
main.py
───────
Entry point.  Run with:  python main.py

Goal clip recording is triggered when ALL three conditions are true:
  1. Ball is inside the goal zone   (GOAL_ZONE_NEAR ≤ z ≤ GOAL_ZONE_FAR)
  2. Ball velocity exceeds minimum  (velocity > GOAL_MIN_VELOCITY)
  3. Cooldown has elapsed           (≥ GOAL_SEND_INTERVAL s since last trigger)

Press  Q  to quit.
"""

import time
import cv2

import config
import server
import recording
from sources   import build_source
from detection import detect_ball
from tracker   import BallTracker
from drawing   import draw_ball, draw_mode_label


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
                in_zone    = config.GOAL_ZONE_NEAR <= result["z_m"] <= config.GOAL_ZONE_FAR
                fast_enough = result["velocity"] > config.GOAL_MIN_VELOCITY
                cooldown_ok = (current_time - last_trigger_time) >= config.GOAL_SEND_INTERVAL

                if in_zone and fast_enough and cooldown_ok:
                    server.record_velocity(result["velocity"], result["z_m"])
                    recorder.trigger_goal(current_time, result["velocity"], result["z_m"])
                    last_trigger_time = current_time
                # ─────────────────────────────────────────────────────────

            else:
                tracker.reset()

            draw_mode_label(frame, "camera")

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

    server.start()

    source   = build_source(config)
    tracker  = BallTracker(config)
    recorder = recording.GoalRecorder(server, config)

    run_loop(source, tracker, recorder)

    print("[INFO] Tracker stopped.")


if __name__ == "__main__":
    main()
