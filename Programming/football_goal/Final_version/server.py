"""
server.py
─────────
Lightweight Flask web server that runs in a background thread alongside
the tracker.  It exposes two endpoints:

    GET /velocity       → latest recorded reading (JSON)
    GET /history        → all readings since startup (JSON)
    GET /               → simple HTML dashboard (auto-refreshes every 2 s)

The main loop calls  record_velocity(velocity, z_m)  whenever the ball is
inside the target distance window.  That call is thread-safe and non-blocking.
"""

import threading
import time
from collections import deque
from datetime import datetime

from flask import Flask, jsonify

# ── Shared state (guarded by a lock) ─────────────────────────────────────────
_lock    = threading.Lock()
_latest  = None                          # dict | None
_history = deque(maxlen=200)             # keep last 200 readings in RAM

app = Flask(__name__)


# ── Public API called from main.py ────────────────────────────────────────────

def record_velocity(velocity: float, z_m: float) -> None:
    """
    Store a new velocity reading.  Safe to call from any thread.
    """
    entry = {
        "timestamp":    datetime.now().isoformat(timespec="milliseconds").replace("T", " "),
        "velocity_m_s": round(velocity, 4),
        "distance_m":   round(z_m, 4),
    }
    with _lock:
        global _latest
        _latest = entry
        _history.append(entry)

    print(f"[SERVER] Recorded  vel={velocity:.3f} m/s  z={z_m:.3f} m")


def start(host: str = "0.0.0.0", port: int = 5000) -> None:
    """
    Launch Flask in a daemon thread so it dies automatically when main exits.
    """
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
    """Return the most recent reading as JSON."""
    with _lock:
        data = _latest
    if data is None:
        return jsonify({"status": "no_data",
                        "message": "No reading yet — ball may not be in range."}), 204
    return jsonify({"status": "ok", "data": data})


@app.route("/history")
def get_history():
    """Return all stored readings as a JSON array."""
    with _lock:
        data = list(_history)
    return jsonify({"status": "ok", "count": len(data), "data": data})


@app.route("/")
def dashboard():
    """Minimal HTML dashboard that polls /velocity every 2 seconds."""
    return """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Ball Tracker – Live</title>
  <style>
    body  { font-family: monospace; background: #111; color: #eee;
            display: flex; flex-direction: column; align-items: center;
            justify-content: center; min-height: 100vh; margin: 0; }
    h1    { color: #0ff; margin-bottom: 0.3em; }
    .card { background: #1e1e1e; border: 1px solid #333; border-radius: 8px;
            padding: 2em 3em; text-align: center; min-width: 320px; }
    .val  { font-size: 3em; color: #0f0; margin: 0.2em 0; }
    .sub  { color: #888; font-size: 0.85em; }
    .dot  { display: inline-block; width: 10px; height: 10px;
            border-radius: 50%; background: #0f0;
            animation: blink 1s step-start infinite; }
    @keyframes blink { 50% { opacity: 0; } }
  </style>
</head>
<body>
  <div class="card">
    
    <h1>SMART FOOTBALL GOAL</h1>
    
    <hr style="border-color:#333; margin: 2em 1">
    
    <h3>Ball Velocity Tracker</h3>
    <div class="sub">Target zone: 29.5 – 30.5 cm &nbsp;<span class="dot"></span></div>
    
    <div class="val">
    <span id="vel">—</span>
    <span class="unit">m/s</span>
    </div>

    <hr style="border-color:#333; margin: 1em 0">

    <h3>Additional Data</h3>
    <div class="sub">Exact distance measured: &nbsp;<span id="dist">—</span> m</div>
    <div class="sub">Last timestamp: &nbsp;<class="sub" id="ts" style="margin-top:0.5em">—</div>


    <hr style="border-color:#333; margin: 1em 0">
    <h3>Type in your browser to enter this page:</h3>
    <h3>192.168.1.148:500</h3>

  </div>
  <script>
    async function poll() {
      try {
        const r = await fetch('/velocity');
        if (r.status === 204) { document.getElementById('vel').textContent = '—'; return; }
        const j = await r.json();
        document.getElementById('vel').textContent  = j.data.velocity_m_s.toFixed(3);
        document.getElementById('dist').textContent = j.data.distance_m.toFixed(2);
        document.getElementById('ts').textContent   = j.data.timestamp;
      } catch(e) { console.warn(e); }
    }
    poll();
    setInterval(poll, 2000);
  </script>
</body>
</html>"""
