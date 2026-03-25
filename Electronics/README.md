## ⚡ Electronics: High-Performance Edge Computing

The electronic heart of SmartGoal is designed for low-latency image processing and stable high-speed data acquisition.

### 🧠 Core Components
- **Raspberry Pi 4 (8GB RAM):** Handles the parallel execution of the OS, camera stream, and OpenCV mathematical calculations.
- **Sony IMX219 Camera Module:** An 8MP sensor capable of high-speed video modes (90-120 FPS), connected via a dedicated 15-pin **CSI (Camera Serial Interface)**.
- **Power Management:** 5V/3A USB-C power delivery with an integrated 10,000mAh battery for 4+ hours of pitch-side operation.
- **Thermal Solution:** Active cooling (PWM Fan) and aluminum heatsinks to prevent CPU throttling during intensive 3D math processing.

### 🔌 Connectivity & Signal Flow
1. **Raw Input:** The IMX219 sensor sends raw Bayer data through the CSI bus to the Pi's GPU.
2. **Hardware Decoding:** The ISP (Image Signal Processor) converts data to a BGR888 array.
3. **Feedback Output:** Real-time data is displayed via Micro-HDMI or transmitted over 5GHz Wi-Fi for remote monitoring.

