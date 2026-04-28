"""
recording.py
────────────
Parallel goal-clip recorder.

Architecture
───────────
  ┌─ main loop ──────────────────────────────────────┐
  │  GoalRecorder.add_frame(annotated_frame, ts)      │  ← every frame
  │  GoalRecorder.trigger_goal(ts, velocity, z_m)     │  ← on goal detection
  └───────────────────────────────────────────────────┘
                        │ (thread-safe queue)
  ┌─ background thread ───────────────────────────────┐
  │  Waits POST_TRIGGER_S after each trigger           │
  │  Slices the rolling buffer → writes slow-mo MP4   │
  │  Calls server.register_video(path)                 │
  └───────────────────────────────────────────────────┘

Rolling buffer
──────────────
  • Stores (timestamp, frame_copy) tuples.
  • Frames older than BUFFER_MAX_AGE_S are pruned every add_frame() call.
  • Frame copies are made immediately so the main loop can reuse its array.
"""

import os
import time
import threading
from collections import deque
from pathlib import Path

import cv2


class GoalRecorder:
    def __init__(self, server_module, cfg):
        self._server   = server_module
        self._cfg      = cfg
        self._buf_lock = threading.Lock()
        self._buf      = deque()          # (timestamp, np.ndarray BGR)
        self._trig_lock = threading.Lock()
        self._triggers  = []              # (trigger_ts, velocity, z_m)

        Path(cfg.VIDEO_DIR).mkdir(exist_ok=True)

        self._thread = threading.Thread(
            target=self._worker, daemon=True, name="goal-recorder"
        )
        self._thread.start()
        print("[RECORDER] Started — saving clips to '{}/'".format(cfg.VIDEO_DIR))

    # ── Public API (called from main loop) ────────────────────────────────────

    def add_frame(self, frame, timestamp: float) -> None:
        """
        Feed every annotated frame into the rolling buffer.
        Call this for EVERY frame, regardless of goal state.
        """
        with self._buf_lock:
            self._buf.append((timestamp, frame.copy()))
            # Prune frames older than the rolling window
            cutoff = timestamp - self._cfg.BUFFER_MAX_AGE_S
            while self._buf and self._buf[0][0] < cutoff:
                self._buf.popleft()

    def trigger_goal(self, timestamp: float, velocity: float, z_m: float) -> None:
        """
        Signal a goal event.  The clip will be saved once POST_TRIGGER_S
        seconds of footage have been collected after *timestamp*.
        """
        with self._trig_lock:
            self._triggers.append((timestamp, velocity, z_m))
        print(f"[RECORDER] Goal trigger queued  vel={velocity:.2f} m/s  z={z_m:.2f} m")

    # ── Background worker ─────────────────────────────────────────────────────

    def _worker(self) -> None:
        while True:
            time.sleep(0.05)
            now   = time.time()
            ready = []

            with self._trig_lock:
                pending = []
                for item in self._triggers:
                    if now >= item[0] + self._cfg.POST_TRIGGER_S:
                        ready.append(item)
                    else:
                        pending.append(item)
                self._triggers = pending

            for trigger_ts, velocity, z_m in ready:
                try:
                    self._save_clip(trigger_ts, velocity, z_m)
                except Exception as exc:
                    print(f"[RECORDER] Error saving clip: {exc}")

    # ── Clip writer ───────────────────────────────────────────────────────────

    def _save_clip(self, trigger_ts: float, velocity: float, z_m: float) -> None:
        cfg = self._cfg

        # Extract the relevant window from the rolling buffer
        window_start = trigger_ts - cfg.PRE_TRIGGER_S
        window_end   = trigger_ts + cfg.POST_TRIGGER_S

        with self._buf_lock:
            frames = [
                (ts, f) for ts, f in self._buf
                if window_start <= ts <= window_end
            ]

        if len(frames) < 2:
            print("[RECORDER] Not enough frames in buffer — clip skipped.")
            return

        # Estimate real capture fps from frame timestamps
        real_duration = frames[-1][0] - frames[0][0]
        real_fps      = len(frames) / real_duration if real_duration > 0 else 30.0
        write_fps     = max(real_fps / cfg.SLOWMO_FACTOR, 1.0)

        # Build output path
        ts_str   = time.strftime("%Y%m%d_%H%M%S", time.localtime(trigger_ts))
        out_path = str(Path(cfg.VIDEO_DIR) / f"goal_{ts_str}.mp4")

        h, w = frames[0][1].shape[:2]
        fourcc = cv2.VideoWriter_fourcc(*"mp4v")
        writer = cv2.VideoWriter(out_path, fourcc, write_fps, (w, h))

        for _, frame in frames:
            writer.write(frame)
        writer.release()

        print(
            f"[RECORDER] Saved '{out_path}'  "
            f"frames={len(frames)}  "
            f"real={real_fps:.1f} fps → write={write_fps:.1f} fps  "
            f"({cfg.SLOWMO_FACTOR}× slow-mo)"
        )

        # Hand the clip off to the web server
        self._server.register_video(out_path)
