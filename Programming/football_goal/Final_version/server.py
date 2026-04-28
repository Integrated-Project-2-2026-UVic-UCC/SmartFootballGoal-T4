"""
server.py
─────────
Flask web server running in a background thread.

Endpoints
─────────
  GET /              → live dashboard (velocity + last 2 goal replays)
  GET /velocity      → latest velocity reading (JSON)
  GET /history       → all velocity readings since startup (JSON)
  GET /videos        → list of available goal clips (JSON)
  GET /video/<name>  → stream a goal clip (MP4)

Public API (called from other modules)
───────────────────────────────────────
  record_velocity(velocity, z_m)   → store a live reading
  register_video(filepath)         → add a new goal clip; keeps only last 2
  start(host, port)                → launch Flask in a daemon thread
"""

import os
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, send_from_directory

# ── Shared state ──────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_latest  = None                   # latest velocity reading (dict | None)
_history = deque(maxlen=200)      # rolling history of readings
_videos  = []                     # paths of the last 2 goal clips (oldest first)

app = Flask(__name__)


# ── Public API ────────────────────────────────────────────────────────────────

def record_velocity(velocity: float, z_m: float) -> None:
    """Store a new velocity reading.  Thread-safe, non-blocking."""
    entry = {
        "timestamp":    datetime.now().isoformat(timespec="milliseconds").replace("T", " "),
        "velocity_m_s": round(velocity, 4),
        "distance_m":   round(z_m,      4),
    }
    with _lock:
        global _latest
        _latest = entry
        _history.append(entry)
    print(f"[SERVER] Recorded  vel={velocity:.3f} m/s  z={z_m:.3f} m")


def register_video(filepath: str) -> None:
    """
    Register a new goal clip.
    Keeps only the last 2 clips — deletes the oldest from disk when a 3rd arrives.
    """
    with _lock:
        global _videos
        if len(_videos) >= 2:
            to_delete = _videos.pop(0)      # remove oldest from list
            try:
                os.remove(to_delete)
                print(f"[SERVER] Deleted old clip: {to_delete}")
            except OSError as e:
                print(f"[SERVER] Could not delete '{to_delete}': {e}")
        _videos.append(filepath)
    print(f"[SERVER] Registered clip: {filepath}  (total kept: {len(_videos)})")


def start(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Launch Flask in a daemon thread."""
    thread = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
        name="flask-server",
    )
    thread.start()
    print(f"[SERVER] Listening on  http://{host}:{port}")


# ── Flask routes ──────────────────────────────────────────────────────────────

@app.route("/velocity")
def get_velocity():
    with _lock:
        data = _latest
    if data is None:
        return jsonify({"status": "no_data",
                        "message": "No reading yet — ball not in range."}), 204
    return jsonify({"status": "ok", "data": data})


@app.route("/history")
def get_history():
    with _lock:
        data = list(_history)
    return jsonify({"status": "ok", "count": len(data), "data": data})


@app.route("/videos")
def list_videos():
    with _lock:
        names = [Path(p).name for p in _videos]
    return jsonify({"status": "ok", "count": len(names), "videos": names})


@app.route("/video/<path:filename>")
def serve_video(filename):
    """Stream a goal clip — supports HTTP range requests for seek."""
    # Determine the folder from the registered paths
    with _lock:
        folders = list({str(Path(p).parent) for p in _videos})
    # Search in all known folders (should be just one: VIDEO_DIR)
    for folder in folders:
        candidate = Path(folder) / filename
        if candidate.exists():
            return send_from_directory(folder, filename, conditional=True)
    return jsonify({"error": "Video not found"}), 404


@app.route("/")
def dashboard():
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Smart Football Goal</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

    body {
      font-family: 'Segoe UI', monospace;
      background: #0a0a0f;
      color: #e0e0e0;
      min-height: 100vh;
      padding: 1.5rem;
    }

    h1 {
      text-align: center;
      color: #00ffcc;
      font-size: 1.8rem;
      letter-spacing: 3px;
      text-transform: uppercase;
      margin-bottom: 0.3rem;
    }
    .subtitle {
      text-align: center;
      color: #555;
      font-size: 0.75rem;
      letter-spacing: 2px;
      margin-bottom: 2rem;
    }

    .grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.2rem;
      max-width: 860px;
      margin: 0 auto;
    }
    @media (max-width: 600px) { .grid { grid-template-columns: 1fr; } }

    .card {
      background: #13131a;
      border: 1px solid #222;
      border-radius: 12px;
      padding: 1.4rem 1.6rem;
    }
    .card h2 {
      font-size: 0.7rem;
      letter-spacing: 2px;
      text-transform: uppercase;
      color: #444;
      margin-bottom: 1rem;
    }

    /* ── Live velocity ── */
    .vel-value {
      font-size: 4rem;
      font-weight: 700;
      color: #00ff88;
      line-height: 1;
    }
    .vel-unit { font-size: 1rem; color: #555; margin-left: 4px; }
    .meta { font-size: 0.78rem; color: #555; margin-top: 0.8rem; }
    .meta span { color: #888; }

    /* ── Status dot ── */
    .dot {
      display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: #00ff88;
      animation: blink 1.2s step-start infinite;
      margin-right: 6px;
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* ── Goal replays ── */
    .replays { grid-column: 1 / -1; }
    .replay-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1rem;
      margin-top: 0.5rem;
    }
    @media (max-width: 600px) { .replay-grid { grid-template-columns: 1fr; } }

    .replay-slot {
      background: #0d0d14;
      border: 1px solid #1e1e2e;
      border-radius: 8px;
      overflow: hidden;
      min-height: 140px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
    }
    .replay-slot video {
      width: 100%;
      border-radius: 0;
      display: block;
    }
    .replay-label {
      font-size: 0.65rem;
      letter-spacing: 1px;
      color: #333;
      padding: 6px;
      text-align: center;
    }
    .no-video { font-size: 0.75rem; color: #2a2a3a; }

    /* ── Zone info ── */
    .zone-badge {
      display: inline-block;
      background: #0d1f0d;
      border: 1px solid #1a3a1a;
      color: #00cc66;
      font-size: 0.7rem;
      border-radius: 20px;
      padding: 3px 12px;
      margin-top: 0.5rem;
    }
  </style>
</head>
<body>

  <h1>⚽ Smart Football Goal</h1>
  <div class="subtitle">Real-time ball velocity tracker</div>

  <div class="grid">

    <!-- Live velocity card -->
    <div class="card">
      <h2><span class="dot"></span>Live velocity</h2>
      <div>
        <span class="vel-value" id="vel">—</span>
        <span class="vel-unit">m/s</span>
      </div>
      <div class="zone-badge">Goal zone: 29.5 – 30.5 m</div>
      <div class="meta">
        Distance &nbsp;<span id="dist">—</span> m<br>
        Last update &nbsp;<span id="ts">—</span>
      </div>
    </div>

    <!-- Stats card -->
    <div class="card">
      <h2>Session stats</h2>
      <div class="meta" style="font-size:0.9rem; line-height:2">
        Goals recorded &nbsp;<span id="goal-count" style="color:#00ff88;font-size:1.4rem">0</span><br>
        Readings sent &nbsp;<span id="reading-count" style="color:#888">0</span>
      </div>
    </div>

    <!-- Goal replays card (full width) -->
    <div class="card replays">
      <h2>Goal replays &nbsp;(last 2 · slow motion)</h2>
      <div class="replay-grid" id="replay-grid">
        <div class="replay-slot"><span class="no-video">No goal yet</span></div>
        <div class="replay-slot"><span class="no-video">No goal yet</span></div>
      </div>
    </div>

  </div><!-- /grid -->

  <script>
    let readingCount = 0;

    async function pollVelocity() {
      try {
        const r = await fetch('/velocity');
        if (r.status === 204) return;
        const j = await r.json();
        if (!j.data) return;
        document.getElementById('vel').textContent  = j.data.velocity_m_s.toFixed(3);
        document.getElementById('dist').textContent = j.data.distance_m.toFixed(2);
        document.getElementById('ts').textContent   = j.data.timestamp;
        readingCount++;
        document.getElementById('reading-count').textContent = readingCount;
      } catch(e) { console.warn('velocity poll:', e); }
    }

    async function pollVideos() {
      try {
        const r = await fetch('/videos');
        const j = await r.json();
        const grid = document.getElementById('replay-grid');
        document.getElementById('goal-count').textContent = j.count;

        // Build two slots
        const slots = ['Previous goal', 'Latest goal'];
        let html = '';
        for (let i = 0; i < 2; i++) {
          const name = j.videos[i];      // may be undefined
          if (name) {
            html += `
              <div class="replay-slot">
                <video controls autoplay muted loop playsinline
                       src="/video/${encodeURIComponent(name)}"></video>
                <div class="replay-label">${slots[i]}</div>
              </div>`;
          } else {
            html += `<div class="replay-slot"><span class="no-video">No goal yet</span></div>`;
          }
        }
        grid.innerHTML = html;
      } catch(e) { console.warn('videos poll:', e); }
    }

    // Initial load
    pollVelocity();
    pollVideos();

    // Polling intervals
    setInterval(pollVelocity, 2000);
    setInterval(pollVideos,   3000);   // slightly offset from velocity poll
  </script>
</body>
</html>"""
