import cv2
import numpy as np
import time
import math
from collections import deque
from picamera2 import Picamera2

# ─── CONFIGURACIÓN ────────────────────────────────────────────────────────────
BALL_DIAMETER_M = 0.205
H_FOV = 62.2
TRAJECTORY_BUF = 20
ALPHA = 0.15          # Suavizado velocidad (más bajo = más suave)
MIN_RADIUS = 4        # Radio mínimo en px para considerar detección válida
CIRCULARITY_THRESHOLD = 0.85  # Por encima → hull limpio, por debajo → RANSAC
RANSAC_ITERATIONS = 100
RANSAC_THRESHOLD = 3.0        # Tolerancia en px para considerar un punto inlier
RANSAC_MIN_INLIER_RATIO = 0.5 # Mínimo 50% del contorno debe encajar

# HSV del balón naranja
LOWER_COLOR = np.array([5,  120,  80])
UPPER_COLOR = np.array([20, 255, 255])

# ─── CÁMARA ───────────────────────────────────────────────────────────────────
picam2 = Picamera2()
config = picam2.create_video_configuration(
    main={"size": (640, 480), "format": "BGR888"},
    controls={
        "FrameDurationLimits": (11111, 11111),
        "ExposureTime": 2000
    }
)
picam2.configure(config)
picam2.start()

IMG_W, IMG_H = 640, 480
CX, CY = IMG_W // 2, IMG_H // 2

# Focal length calculada a partir del FOV horizontal
FOCAL_L = (IMG_W / 2) / math.tan(math.radians(H_FOV / 2))

pts = deque(maxlen=TRAJECTORY_BUF)
prev_data = None
prev_time = time.time()
smoothed_speed_kmh = 0.0

print(f"Iniciando a 90 FPS. Focal Length: {FOCAL_L:.2f} px")


# ────────────────────────── FUNCIONES ───────────────────────────────────────────

def fit_circle_ransac(contour_points):
    pts = contour_points.reshape(-1, 2).astype(np.float32)
    n = len(pts)
    if n < 3:
        return None, None

    best_center = None
    best_radius = None
    best_inliers = 0

    for _ in range(RANSAC_ITERATIONS):
        # Selecciona 3 puntos aleatorios
        idx = np.random.choice(n, 3, replace=False)
        p1, p2, p3 = pts[idx]
        ax, ay = p1
        bx, by = p2
        cx, cy = p3

        # Calcula el círculo que pasa exactamente por esos 3 puntos
        D = 2 * (ax * (by - cy) + bx * (cy - ay) + cx * (ay - by))
        if abs(D) < 1e-6:
            continue  # Puntos colineales, descarta

        ux = ((ax**2 + ay**2) * (by - cy) +
              (bx**2 + by**2) * (cy - ay) +
              (cx**2 + cy**2) * (ay - by)) / D
        uy = ((ax**2 + ay**2) * (cx - bx) +
              (bx**2 + by**2) * (ax - cx) +
              (cx**2 + cy**2) * (bx - ax)) / D
        r = math.sqrt((ax - ux)**2 + (ay - uy)**2)

        # Cuenta cuántos puntos del contorno están cerca de este círculo
        dists = np.sqrt((pts[:, 0] - ux)**2 + (pts[:, 1] - uy)**2)
        inliers = int(np.sum(np.abs(dists - r) < RANSAC_THRESHOLD))

        if inliers > best_inliers:
            best_inliers = inliers
            best_center = (ux, uy)
            best_radius = r

    # Solo acepta si al menos el 50% del contorno encaja como arco circular
    if best_inliers < n * RANSAC_MIN_INLIER_RATIO:
        return None, None

    return best_center, best_radius


def detect_ball(contour):
    """
    A partir de un contorno, intenta extraer center y pixel_diameter fiables.
    1. Convex Hull para tapar agujeros (líneas blancas del balón)
    2. Si es suficientemente circular → radio por área del hull
    3. Si no → RANSAC para ignorar la parte fusionada con otro objeto
    Devuelve (center_px, pixel_diameter) o (None, None) si no es fiable.
    """
    hull = cv2.convexHull(contour)
    area = cv2.contourArea(hull)
    perimeter = cv2.arcLength(hull, True)

    if perimeter == 0:
        return None, None

    circularity = (4 * math.pi * area) / (perimeter ** 2)

    if circularity >= CIRCULARITY_THRESHOLD:
        # Hull es casi un círculo
        radius_eq = math.sqrt(area / math.pi)
        if radius_eq < MIN_RADIUS:
            return None, None
        # Centro por momentos, si se usa minEnclosingCircle es menos estable
        M = cv2.moments(hull)
        if M["m00"] == 0:
            return None, None
        cx = int(M["m10"] / M["m00"])
        cy = int(M["m01"] / M["m00"])
        return (cx, cy), 2 * radius_eq

    else:
        # RANSAC sobre los puntos del hull ya que no es suficientemente correcto
        # Ignora la parte extraña
        center_ransac, radius_ransac = fit_circle_ransac(hull)
        if center_ransac is None or radius_ransac < MIN_RADIUS:
            return None, None
        return (int(center_ransac[0]), int(center_ransac[1])), 2 * radius_ransac


# ─────────────────────────── LOOP PRINCIPAL ─────────────────────────────────────────────
try:
    while True:
        frame = picam2.capture_array()
        t_now = time.time()

        # ── Preprocesado ──
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, LOWER_COLOR, UPPER_COLOR)
        mask = cv2.GaussianBlur(mask, (5, 5), 0)

        # Closing morfológico: rellena huecos pequeños (líneas blancas)
        kernel_close = np.ones((11, 11), np.uint8) #puede generar difuminados, quitar si es necesario
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)

        # Dilate/erode equilibrados para no inflar el contorno
        mask = cv2.dilate(mask, None, iterations=1)
        mask = cv2.erode(mask, None, iterations=1)

        cv2.imshow("Mascara", mask)

        # ── Detección ──
        cnts, _ = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        center_px = None

        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            center_px, pixel_diameter = detect_ball(c)

            if center_px is not None:
                radius_draw = pixel_diameter / 2
                x, y = center_px

                # ── Posición 3D ──
                z_m = (BALL_DIAMETER_M * FOCAL_L) / pixel_diameter
                # Proyección perspectiva correcta para X e Y
                x_m = (x - CX) * z_m / FOCAL_L
                y_m = (y - CY) * z_m / FOCAL_L

                # ── Velocidad ──
                dt = t_now - prev_time
                if prev_data is not None and dt > 0:
                    dx = x_m - prev_data['x']
                    dy = y_m - prev_data['y']
                    dz = z_m - prev_data['z']
                    dist_3d = math.sqrt(dx**2 + dy**2 + dz**2)
                    speed_mps = dist_3d / dt
                    current_kmh = speed_mps * 3.6

                    if current_kmh < 250:  # Filtro de valores absurdos
                        smoothed_speed_kmh = (
                            ALPHA * current_kmh +
                            (1 - ALPHA) * smoothed_speed_kmh
                        )

                prev_data = {'x': x_m, 'y': y_m, 'z': z_m}
                prev_time = t_now

                # ── Dibujo ──
                cv2.circle(frame, center_px, int(radius_draw), (0, 255, 0), 2)
                cv2.circle(frame, center_px, 3, (0, 255, 0), -1)
                cv2.putText(
                    frame,
                    f"{z_m:.2f}m",
                    (x + int(radius_draw) + 5, y),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 1
                )

        if center_px is None:
            # Sin detección fiable — resetea para no contaminar la velocidad
            prev_data = None
            prev_time = t_now

        # ── UI ──
        cv2.rectangle(frame, (10, 10), (320, 60), (0, 0, 0), -1)
        cv2.putText(
            frame,
            f"Vel: {smoothed_speed_kmh:.1f} km/h",
            (20, 45),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2
        )

        cv2.imshow("Smart Goal 3D", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

finally:
    picam2.stop()
    cv2.destroyAllWindows()
