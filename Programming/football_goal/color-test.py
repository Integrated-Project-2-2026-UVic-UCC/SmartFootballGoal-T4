import cv2
import numpy as np
from picamera2 import Picamera2

# Inicializar cámara
picam2 = Picamera2()
config = picam2.create_video_configuration(main={"size": (640, 480), "format": "RGB888"})
picam2.configure(config)
picam2.start()

def nothing(x): pass

# Crear ventana con barras deslizantes
cv2.namedWindow("Trackbars")
cv2.createTrackbar("L-H", "Trackbars", 0, 180, nothing)
cv2.createTrackbar("L-S", "Trackbars", 0, 255, nothing)
cv2.createTrackbar("L-V", "Trackbars", 100, 255, nothing) # Empezamos en 100 para blanco oscuro
cv2.createTrackbar("U-H", "Trackbars", 180, 180, nothing)
cv2.createTrackbar("U-S", "Trackbars", 50, 255, nothing)
cv2.createTrackbar("U-V", "Trackbars", 255, 255, nothing)

print("Mueve las barras hasta que el balón se vea BLANCO y el resto NEGRO.")

try:
    while True:
        frame = picam2.capture_array()
        hsv = cv2.cvtColor(frame, cv2.COLOR_RGB2HSV)

        # Leer valores de las barras
        l_h = cv2.getTrackbarPos("L-H", "Trackbars")
        l_s = cv2.getTrackbarPos("L-S", "Trackbars")
        l_v = cv2.getTrackbarPos("L-V", "Trackbars")
        u_h = cv2.getTrackbarPos("U-H", "Trackbars")
        u_s = cv2.getTrackbarPos("U-S", "Trackbars")
        u_v = cv2.getTrackbarPos("U-V", "Trackbars")

        lower = np.array([l_h, l_s, l_v])
        upper = np.array([u_h, u_s, u_v])

        mask = cv2.inRange(hsv, lower, upper)
        res = cv2.bitwise_and(frame, frame, mask=mask)

        # Mostrar ventanas
        #cv2.imshow("Original", cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
        cv2.imshow("Original2",frame)
        cv2.imshow("Mascara (Blanco = Detectado)", mask)
        
        if cv2.waitKey(1) & 0xFF == ord('q'): break
finally:
    picam2.stop()
    cv2.destroyAllWindows()