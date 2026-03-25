<!-- TOP SECTION -->
<div align="center">
  <h1>⚽ SmartGoal – AI-Powered Intelligent Football Goal</h1>
  <p>
    <i>High-speed 3D tracking, real-time ball analytics, and professional goal detection.</i>
  </p>
  <img src="https://img.shields.io/badge/Hardware-Raspberry%20Pi%204-red?style=for-the-badge&logo=raspberrypi" alt="Raspberry Pi 4">
  <img src="https://img.shields.io/badge/Software-Python%20%2B%20OpenCV-blue?style=for-the-badge&logo=python" alt="Python OpenCV">
  <img src="https://img.shields.io/badge/Performance-90%20FPS-green?style=for-the-badge" alt="90 FPS">
</div>

---

## 🌍 The Vision: Professional Analytics for Everyone

In recreational football, disputes over goal-line clearances and the lack of performance data are common. SmartGoal bridges the gap between amateur play and professional stadiums. 

Using **Advanced Computer Vision**, SmartGoal doesn't just count points—it analyzes the game. It transforms standard goalposts into an intelligent arena capable of measuring strike speed and ball trajectory in real-time, providing an immersive, data-driven experience for players of all levels.

---

## 🚀 Key Technical Innovations

Unlike traditional beam-break sensors, SmartGoal uses an **Optical Processing Pipeline** to "see" the ball:

- **90 FPS High-Speed Capture:** Utilizing the Raspberry Pi 4 and Sony IMX219 sensor to eliminate motion blur at strike speeds over 100 km/h.
- **3D Spatial Mapping:** A custom physics engine that calculates the **Z-axis (depth)** using the Pinhole Camera Model. It knows how far the ball is by analyzing its pixel-diameter in real-time.
- **Intelligent Filtering:** An HSV-based color mask combined with a **Circularity Filter** ensures the system only tracks the ball, ignoring shoes, grass, or field lines.

---

## ⚙️ How It Works

### 1️⃣ Optical Acquisition Layer
The high-speed camera captures the pitch at a frame every 11ms. The code forces a low exposure time (shutter speed) to ensure the ball remains a crisp circle even during the hardest shots.

### 2️⃣ Computer Vision Logic
The frame is converted to the **HSV color space**. After applying Gaussian blurs and morphological operations (Erosion/Dilation), the algorithm identifies contours and filters them by **circularity** ($4\pi \times Area / Perimeter^2$).

### 3️⃣ Physics & Speed Engine
Once a ball is confirmed, the system maps its 3D coordinates $(X, Y, Z)$. By calculating the **Euclidean distance** between frames over a precise delta-time, the system outputs the exact velocity in **km/h**.

---

## 🏗️ Technical Stack

### 📦 Hardware
- **Raspberry Pi 4 (8GB):** The core computational brain.
- **Sony IMX219 Sensor:** High-frame-rate 8MP camera.
- **62.2° HFOV Lens:** Optimized for 90cm wide goal coverage.
- **Custom Case:** Weather-protected enclosure for pitch-side deployment.

### 💾 Software (Python 3.11)
- **OpenCV:** Real-time image processing and contour analysis.
- **Picamera2:** Low-level hardware interface for 90-120 FPS capture.
- **NumPy:** Vectorized mathematics for 3D trajectory calculations.
- **EMA Filtering:** Exponential Moving Average for speed smoothing.

---

## 🎮 Core Functionalities

| Feature | Technical Implementation |
|----------|---------|
| **Instant Speedometer** | Real-time calculation of strike velocity in km/h. |
| **3D Depth Tracking** | Detects ball movement toward/away from the camera. |
| **Smart Detection** | Differentiates between the ball and player movement. |
| **High-Speed Path** | Displays a 20-frame visual "tail" of the ball's flight. |
| **Goal Validation** | Objective confirmation when the ball crosses the Z-plane. |

---

## 🔮 Future Development

We are currently working on expanding the system's intelligence:

- **Shot Heatmaps:** Visualizing where in the goal most strikes occur.
- **Mobile Integration:** Syncing match stats directly to an app/webpage.


---

<div align="center">
  <br>
  <strong>SmartGoal Project</strong><br>
  <i>Redefining the Beautiful Game with Computer Vision.</i>
</div>
