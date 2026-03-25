
## 💻 Programming: The Vision Pipeline

The software architecture is a custom-built **Object Tracking & Physics Engine** written in Python 3.

### 👁️ Computer Vision Pipeline
- **HSV Space Isolation:** To handle changing outdoor light, the code converts frames to **HSV (Hue, Saturation, Value)**. This allows for stable color tracking even under heavy shadows or bright sunlight.
- **Morphological Filtering:** Uses **Gaussian Blurring**, **Erosion**, and **Dilation** to eliminate "salt and pepper" noise from the grass and player movement.
- **Circularity Algorithm:** To prevent tracking non-ball objects, every detected shape is put through a circularity test:
  $$Circularity = 4\pi \times \frac{Area}{Perimeter^2}$$
  *Only objects with a ratio $> 0.6$ (indicating a spherical shape) are accepted.*

### 📐 3D Physics Engine
- **Depth Estimation (Z-axis):** Based on the **Pinhole Camera Model**, the code calculates ball distance by comparing its pixel diameter to its real-world size (22.5cm):
  $$Z = \frac{BallDiameter \times FocalLength}{PixelDiameter}$$
- **3D Velocity Vector:** The system tracks the Euclidean distance between frames in a 3D coordinate system $(X, Y, Z)$:
  $$\text{Speed} = \frac{\sqrt{\Delta X^2 + \Delta Y^2 + \Delta Z^2}}{\Delta Time}$$
- **Smoothing:** A weighted **Exponential Moving Average (EMA)** filter stabilizes the speed output, removing jitter from pixel noise.
