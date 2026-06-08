<div align="center">
  <h1>⚽ SmartGoal</h1>
</div>

### Computer-vision football goal with real-time ball tracking, speed measurement, and automatic slow-motion recording.

We are four Mechatronics Engineering students at UVIC and we built SmartGoal as our Integrated Projects II final prototype. The goal detects shots, measures ball speed in real time, records a slow-motion clip of every goal, and serves everything through a web dashboard hosted on the Raspberry Pi itself — no internet connection, no external infrastructure.

- Fully open-source — **hardware**, **software**, **firmware**.
- Runs on a **Raspberry Pi 4b** with a standard **Camera Module V2**.
- Ball tracking at up to **90 FPS** using OpenCV colour segmentation.
- **3D position and velocity** calculated from a single camera using the pinhole camera model.
- **4× slow-motion** goal clips saved automatically and accessible from any device on the local network.
- **Headless operation** — no monitor required after first setup.

---

## Built for tinkerers

SmartGoal is **not a finished product**. We built it in a university workshop with aluminium profiles, a drill press, and a 3D printer, and we expect you to do the same.

The aluminium goal frame is 100 cm wide, 65 cm tall, and 30 cm deep. The camera mounts on a custom support arm 60 cm behind and 35 cm above the crossbar. All structural parts are bolted together with M10 hardware — no welding required.

If you want a simpler build, you can mount the camera system on any existing goal of similar dimensions without building the frame from scratch.

---

## How it works

The camera captures frames at up to 90 FPS with a fixed 2000 µs exposure to keep the ball sharp at high speeds. Each frame is converted to HSV colour space and thresholded to isolate the ball. The largest matching contour is fitted with a minimum enclosing circle. If the circle radius exceeds the minimum threshold, the detection is accepted.

The detected radius in pixels is used to compute depth (Z axis) through the pinhole camera model: knowing the real ball diameter (20.4 cm) and the apparent pixel diameter, the system back-calculates the distance to the camera. Lateral position (X, Y) is derived from the pixel offset from the image centre scaled by the depth.

Velocity is the 3D Euclidean distance between consecutive positions divided by the elapsed time between frames, smoothed with an exponential moving average (α = 0.7).

A goal is registered when three conditions are met simultaneously: the ball is inside the configured depth window, speed exceeds the minimum threshold, and the cooldown period since the last trigger has elapsed.

When a goal is triggered, the system slices a 2-second window from the rolling frame buffer (1 s before and 1 s after the event), writes it at 1/4 of the real frame rate to produce 4× slow motion, re-encodes it to H.264 with ffmpeg for browser compatibility, and registers it with the web server.

---

# Getting started

## 1. Hardware

### 1.1 Electronics

| Component | Notes |
|-----------|-------|
| Raspberry Pi 4b (4 GB or 8 GB) | Main processing unit |
| Raspberry Pi Camera Module V2 | Connected via CSI ribbon cable |
| USB-C power adapter (5 V / 3 A minimum) | Official Raspberry Pi adapter recommended |

Power the Raspberry Pi through the USB-C port. The camera draws power directly from the CSI connector — no additional wiring is needed.

### 1.2 Mechanical build

The goal frame uses 50 × 50 × 2 mm hollow square aluminium profiles bolted together with metallic angle brackets and M10 hardware.

**Dimensions:**
- Width: 1000 mm
- Height: 650 mm  
- Depth: 300 mm
- Rear support angle: 65.2° (calculated from the 650/300 geometry)
- Camera support arm: 600 mm horizontal + 350 mm vertical extension

**3D-printed parts** (PLA, designed in PTC Creo):
- End caps for open profile ends (45.90 × 43.40 mm, 2.50 mm height)
- Camera and Raspberry Pi enclosure support base (110 × 110 mm)
- Auxiliary fixation bracket (35 × 25 mm)

All STL files are in the `mechanical/` folder.

---

## 2. Software setup

### 2.1 Install dependencies

```bash
sudo apt update
sudo apt install -y python3-pip ffmpeg network-manager
pip3 install opencv-python picamera2 flask numpy
```

### 2.2 Clone the repository

```bash
git clone https://github.com/your-username/SmartGoal.git
cd SmartGoal
```

### 2.3 Configure the system

All parameters are in `config.py`:

```python
BALL_DIAMETER_M    = 0.204       # real ball diameter in metres
H_FOV              = 62.2        # horizontal field of view of your camera
IMG_W, IMG_H       = 640, 480    # capture resolution
CALIBRATION_FACTOR = 2.14        # lens distortion correction — recalibrate for your setup
HSV_LOWER          = (108, 134, 121)   # lower HSV bound for ball colour
HSV_UPPER          = (121, 255, 255)   # upper HSV bound for ball colour
GOAL_ZONE_NEAR     = 0.895       # near edge of goal plane in metres
GOAL_ZONE_FAR      = 0.905       # far edge of goal plane in metres
GOAL_MIN_VELOCITY  = 1.0         # minimum speed to register a goal (m/s)
SLOWMO_FACTOR      = 4           # slow-motion multiplier for saved clips
```

The HSV bounds and calibration factor depend on your ball colour and lens. See the calibration section below.

### 2.4 Run

```bash
python3 main.py
```

On startup the system creates a Wi-Fi hotspot named **SFGoal** (password: **football1**). Connect any device to that network and open `http://192.168.4.1:5000` in a browser to access the dashboard.

If an HDMI display is connected, a live preview window opens automatically. Without a display the system runs in headless mode — tracking, recording, and the web server all continue to work.

Press **Q** in the preview window or `Ctrl+C` in the terminal to stop.

---

## 3. Calibration

### 3.1 Ball colour (HSV thresholds)

Run the calibration tool with the system live:

```bash
python3 calibrate_hsv.py
```

Adjust the sliders until only the ball is visible in the mask preview. Copy the resulting `HSV_LOWER` and `HSV_UPPER` values into `config.py`.

### 3.2 Camera field of view

```bash
python3 calibrate_fov.py
```

Press `+` / `-` to adjust the crop factor until the goal opening fills the frame comfortably. Press `S` to save the resulting `H_FOV` value to `config.py`.

### 3.3 Depth calibration

Place the ball at a known distance from the camera (e.g. 1.00 m) and run the system. Read the reported Z value from the terminal or dashboard. Adjust `CALIBRATION_FACTOR` in `config.py` using:

```
CALIBRATION_FACTOR = CALIBRATION_FACTOR × (real_distance / reported_Z)
```

Repeat until the reported distance matches the real distance within acceptable error.

---

## 4. File structure

```
SmartGoal/
├── main.py          # entry point — initialises all components and runs the capture loop
├── config.py        # all tunable constants
├── detection.py     # detect_ball() — HSV segmentation and circle fitting
├── tracker.py       # BallTracker — 3D position and velocity from pixel detections
├── recording.py     # GoalRecorder — rolling buffer and background video writer
├── server.py        # Flask web dashboard
├── hotspot.py       # Wi-Fi hotspot management
├── sources.py       # CameraSource — PiCamera2 wrapper
├── drawing.py       # draw_ball() — live preview annotation
├── calibrate_fov.py # interactive FOV calibration tool
└── mechanical/      # STL files and CAD drawings
```

---

## 5. Troubleshooting

**Camera not found / PiCamera2 error**

Make sure no other process is using the camera:

```bash
sudo pkill -f python3
sudo fuser -k /dev/video0 2>/dev/null
sleep 2
python3 main.py
```

**Hotspot not starting**

```bash
sudo apt install -y network-manager
sudo systemctl enable NetworkManager
sudo systemctl start NetworkManager
```

**Videos not playing in the browser**

ffmpeg must be installed for H.264 re-encoding:

```bash
sudo apt install -y ffmpeg
```

**Ball not detected**

Recalibrate the HSV thresholds under your current lighting conditions. Detection is sensitive to ambient light changes — the system works best under consistent indoor lighting.

---

## Built by

Sergi Ocaña, Mireia Sabaté, Martí Sayago, Oleguer Treserra  
Degree in Mechatronics Engineering — UVIC, 2026

Tutor: Clara I. Sandino, Moises Garin Escriva
