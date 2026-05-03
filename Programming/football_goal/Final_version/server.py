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

  GET /hotspot       → JSON with SSID, password, IP (for display / QR)

Captive portal
──────────────
  A second Flask instance listens on port 80.
  Any path on port 80 redirects straight to the dashboard on port 5000.
  This makes phones show the "Open in browser" prompt automatically
  when they join the WiFi hotspot.

Public API (called from other modules)
───────────────────────────────────────
  record_velocity(velocity, z_m)         → store a live reading
  register_video(filepath)               → add a new goal clip; keeps only last 2
  set_hotspot_info(ssid, password, url)  → store hotspot connection details
  start(host, port)                      → launch Flask in a daemon thread
"""

import os
import threading
from collections import deque
from datetime import datetime
from pathlib import Path

from flask import Flask, jsonify, redirect, send_from_directory

# ── Shared state ──────────────────────────────────────────────────────────────
_lock    = threading.Lock()
_latest  = None                   # latest velocity reading (dict | None)
_history = deque(maxlen=200)      # rolling history of readings
_videos  = []                     # paths of the last 2 goal clips (oldest first)
_hotspot = {                      # filled by set_hotspot_info()
    "ssid":     "SFGoal",
    "password": "football1",
    "url":      "http://192.168.4.1:5000",
}

app         = Flask(__name__)
_portal_app = Flask("captive_portal")   # port-80 redirect server


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
            to_delete = _videos.pop(0)
            try:
                os.remove(to_delete)
                print(f"[SERVER] Deleted old clip: {to_delete}")
            except OSError as e:
                print(f"[SERVER] Could not delete '{to_delete}': {e}")
        _videos.append(filepath)
    print(f"[SERVER] Registered clip: {filepath}  (total kept: {len(_videos)})")


def set_hotspot_info(ssid: str, password: str, url: str) -> None:
    """Store WiFi hotspot connection details so the dashboard can display them."""
    with _lock:
        _hotspot["ssid"]     = ssid
        _hotspot["password"] = password
        _hotspot["url"]      = url


def start(host: str = "0.0.0.0", port: int = 5000) -> None:
    """Launch the main Flask app and the captive-portal redirect on port 80."""
    # Main dashboard
    t_main = threading.Thread(
        target=lambda: app.run(host=host, port=port, debug=False, use_reloader=False),
        daemon=True,
        name="flask-server",
    )
    t_main.start()
    print(f"[SERVER] Dashboard →  http://{host}:{port}")

    # Captive portal (port 80) — silently skip if port 80 needs root
    try:
        t_portal = threading.Thread(
            target=lambda: _portal_app.run(
                host=host, port=80, debug=False, use_reloader=False
            ),
            daemon=True,
            name="captive-portal",
        )
        t_portal.start()
        print(f"[SERVER] Captive portal →  http://{host}:80  (redirects to :{port})")
    except Exception as exc:
        print(f"[SERVER] Captive portal skipped ({exc}) — run as root for port 80.")


# ── Captive portal app (port 80) ──────────────────────────────────────────────

@_portal_app.route("/", defaults={"path": ""})
@_portal_app.route("/<path:path>")
def captive_redirect(path):
    """Redirect every request to the main dashboard."""
    with _lock:
        url = _hotspot["url"]
    return redirect(url, code=302)


# ── Main Flask routes ─────────────────────────────────────────────────────────

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


@app.route("/hotspot")
def get_hotspot():
    with _lock:
        info = dict(_hotspot)
    return jsonify({"status": "ok", "data": info})


@app.route("/qr/wifi")
def serve_qr_wifi():
    """QR to connect to the WiFi (QR_wifi.jpg)."""
    folder = str(Path(__file__).parent)
    return send_from_directory(folder, "QR_wifi.jpg")


@app.route("/qr/server")
def serve_qr_server():
    """QR to connect do the webserver (QR_server.png)."""
    folder = str(Path(__file__).parent)
    return send_from_directory(folder, "QR_server.png")


@app.route("/video/<path:filename>")
def serve_video(filename):
    with _lock:
        folders = list({str(Path(p).parent) for p in _videos})
    for folder in folders:
        candidate = Path(folder) / filename
        if candidate.exists():
            return send_from_directory(folder, filename, conditional=True)
    return jsonify({"error": "Video not found"}), 404


@app.route("/")
def dashboard():
    return r"""<!DOCTYPE html>
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
      max-width: 960px;
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
    .vel-value  { font-size: 4rem; font-weight: 700; color: #00ff88; line-height: 1; }
    .vel-unit   { font-size: 1rem; color: #555; margin-left: 4px; }
    .meta       { font-size: 0.78rem; color: #555; margin-top: 0.8rem; }
    .meta span  { color: #888; }

    /* ── Status dot ── */
    .dot {
      display: inline-block; width: 8px; height: 8px;
      border-radius: 50%; background: #00ff88;
      animation: blink 1.2s step-start infinite;
      margin-right: 6px;
    }
    @keyframes blink { 50% { opacity: 0; } }

    /* ── Goal replays ── */
    .replays      { grid-column: 1 / -1; }
    .replay-grid  {
      display: grid; grid-template-columns: 1fr 1fr;
      gap: 1rem; margin-top: 0.5rem;
    }
    @media (max-width: 600px) { .replay-grid { grid-template-columns: 1fr; } }

    .replay-slot {
      background: #0d0d14;
      border: 1px solid #1e1e2e;
      border-radius: 8px;
      overflow: hidden;
      min-height: 140px;
      display: flex; flex-direction: column;
      align-items: center; justify-content: center;
    }
    .replay-slot video { width: 100%; display: block; }
    .replay-label { font-size: 0.65rem; letter-spacing: 1px; color: #333; padding: 6px; text-align: center; }
    .no-video { font-size: 0.75rem; color: #2a2a3a; }

    /* ── Zone / badge ── */
    .zone-badge {
      display: inline-block;
      background: #0d1f0d; border: 1px solid #1a3a1a;
      color: #00cc66; font-size: 0.7rem;
      border-radius: 20px; padding: 3px 12px; margin-top: 0.5rem;
    }

    /* ── WiFi connect card ── */
    .wifi-card { grid-column: 1 / -1; }

    .wifi-inner {
      display: flex; gap: 1.6rem; align-items: flex-start; flex-wrap: wrap;
    }

    #qr-canvas {
      border: 3px solid #00ffcc33;
      border-radius: 8px;
      image-rendering: pixelated;
      flex-shrink: 0;
    }

    .wifi-details { flex: 1; min-width: 180px; }

    .wifi-row {
      display: flex; align-items: center; gap: 0.6rem;
      background: #0d0d14; border: 1px solid #1e1e2e;
      border-radius: 8px; padding: 0.6rem 0.9rem;
      margin-bottom: 0.5rem;
    }
    .wifi-label { font-size: 0.65rem; letter-spacing: 1px; color: #444; width: 68px; }
    .wifi-value { font-size: 0.9rem; color: #e0e0e0; flex: 1; }
    .copy-btn {
      background: none; border: 1px solid #333; border-radius: 6px;
      color: #555; font-size: 0.65rem; padding: 2px 8px; cursor: pointer;
      transition: color .2s, border-color .2s;
    }
    .copy-btn:hover { color: #00ffcc; border-color: #00ffcc44; }
    .copy-btn.copied { color: #00ff88; border-color: #00ff8844; }

    .wifi-steps {
      font-size: 0.75rem; color: #555; line-height: 2;
      margin-top: 0.6rem; padding-left: 1rem;
    }
    .wifi-steps li { list-style: decimal; }
    .wifi-steps span { color: #888; }
  </style>
</head>
<body>

  <h1>⚽ Smart Football Goal</h1>
  <div class="subtitle">Real-time ball parameters analyzer</div>

  <div class="grid">

    <!-- Live velocity -->
    <div class="card">
      <h2><span class="dot"></span>Live velocity</h2>
      <div>
        <span class="vel-value" id="vel">—</span>
        <span class="vel-unit">m/s</span>
      </div>
      <div class="zone-badge">Goal zone: 59.5 – 60.5 cm</div>
      <div class="meta">
        Distance &nbsp;<span id="dist">—</span> m<br>
        Last update &nbsp;<span id="ts">—</span>
      </div>
    </div>

    <!-- Session stats -->
    <div class="card">
      <h2>Session stats</h2>
      <div class="meta" style="font-size:0.9rem; line-height:2">
        Detected goals &nbsp;<span id="goal-count" style="color:#00ff88;font-size:1.4rem">0</span><br>
      </div>
    </div>

    <!-- Goal replays (full width) -->
    <div class="card replays">
      <h2>Goal replays &nbsp;(last 2 · slow motion)</h2>
      <div class="replay-grid" id="replay-grid">
        <div class="replay-slot"><span class="no-video">No goal yet</span></div>
        <div class="replay-slot"><span class="no-video">No goal yet</span></div>
      </div>
    </div>

    <!-- WiFi connect card (full width) -->
    <div class="card wifi-card">
      <h2>📶  Connect to this goal</h2>
      <div class="wifi-inner">

        <div style="display:flex;gap:1rem;flex-shrink:0;">
          <div style="text-align:center;">
            <img src="/qr/wifi" alt="QR WiFi" width="140" height="140" style="border:3px solid #00ffcc33;border-radius:8px;display:block;">
            <div style="font-size:0.65rem;letter-spacing:1px;color:#444;margin-top:6px;">CONNECT TO THE WiFi</div>
          </div>
          <div style="text-align:center;">
            <img src="/qr/server" alt="QR Servidor" width="140" height="140" style="border:3px solid #00ffcc33;border-radius:8px;display:block;">
            <div style="font-size:0.65rem;letter-spacing:1px;color:#444;margin-top:6px;">OPERN WEBSERVER</div>
          </div>
        </div>

        <div class="wifi-details">
          <div class="wifi-row">
            <span class="wifi-label">NETWORK</span>
            <span class="wifi-value" id="w-ssid">—</span>
            <button class="copy-btn" onclick="copyField('w-ssid', this)">copy</button>
          </div>
          <div class="wifi-row">
            <span class="wifi-label">PASSWORD</span>
            <span class="wifi-value" id="w-pass">—</span>
            <button class="copy-btn" onclick="copyField('w-pass', this)">copy</button>
          </div>
          <div class="wifi-row">
            <span class="wifi-label">URL</span>
            <span class="wifi-value" id="w-url">—</span>
            <button class="copy-btn" onclick="copyField('w-url', this)">copy</button>
          </div>

          <ol class="wifi-steps">
            <li>Connect your phone to the WiFi above</li>
            <li>Open the URL (or scan the QR code) in any browser</li>
            <li>Watch the replays live!</li>
          </ol>
        </div>

      </div>
    </div>

  </div><!-- /grid -->

  <script>
  let _hotspotInfo = null;

  /* ── Copy helper ── */
  function copyField(id, btn) {
    const text = document.getElementById(id).textContent;
    navigator.clipboard.writeText(text).then(() => {
      btn.textContent = '✓';
      btn.classList.add('copied');
      setTimeout(() => { btn.textContent = 'copy'; btn.classList.remove('copied'); }, 1500);
    });
  }

  /* ── Polls ── */
  let _lastVelTs = null;

  async function pollVelocity() {
    try {
      const r = await fetch('/velocity');
      if (r.status === 204) return;
      const j = await r.json();
      if (!j.data) return;
      // Solo actualizar si el timestamp cambió (lectura nueva)
      if (j.data.timestamp === _lastVelTs) return;
      _lastVelTs = j.data.timestamp;
      document.getElementById('vel').textContent  = j.data.velocity_m_s.toFixed(3);
      document.getElementById('dist').textContent = j.data.distance_m.toFixed(2);
      document.getElementById('ts').textContent   = j.data.timestamp;
    } catch(e) { console.warn('velocity poll:', e); }
  }

  let _knownVideos = [];

  async function pollVideos() {
    try {
      const r = await fetch('/videos');
      const j = await r.json();
      document.getElementById('goal-count').textContent = j.count;

      // Solo actualizar el DOM si la lista de vídeos ha cambiado
      const same = j.videos.length === _knownVideos.length &&
                   j.videos.every((v, i) => v === _knownVideos[i]);
      if (same) return;
      _knownVideos = j.videos;

      const grid  = document.getElementById('replay-grid');
      const slots = ['Gol anterior', 'Último gol'];
      let html = '';
      for (let i = 0; i < 2; i++) {
        const name = j.videos[i];
        if (name) {
          html += `
            <div class="replay-slot">
              <video controls autoplay muted loop playsinline
                     src="/video/${encodeURIComponent(name)}"></video>
              <div class="replay-label">${slots[i]}</div>
            </div>`;
        } else {
          html += `<div class="replay-slot"><span class="no-video">Sin gol aún</span></div>`;
        }
      }
      grid.innerHTML = html;
    } catch(e) { console.warn('videos poll:', e); }
  }

  async function pollHotspot() {
    try {
      const r = await fetch('/hotspot');
      const j = await r.json();
      if (!j.data) return;
      const d = j.data;
      document.getElementById('w-ssid').textContent = d.ssid;
      document.getElementById('w-pass').textContent = d.password;
      document.getElementById('w-url').textContent  = d.url;
      _hotspotInfo = d;
    } catch(e) { console.warn('hotspot poll:', e); }
  }

  // Initial load
  pollVelocity();
  pollVideos();
  pollHotspot();

  // Polling intervals
  setInterval(pollVelocity, 2000);
  setInterval(pollVideos,   3000);
  setInterval(pollHotspot, 10000);
  </script>

</body>
</html>"""
