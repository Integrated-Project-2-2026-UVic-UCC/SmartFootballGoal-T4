import cv2
import numpy as np

# RUTA DEL VÍDEO (Cambia esto por el nombre de tu archivo)
VIDEO_PATH = "Football_ball- 7.mp4"

def nothing(x): pass

# Configuración de ventana y barras
cv2.namedWindow("Calibracion")
cv2.createTrackbar("L-H", "Calibracion", 0, 180, nothing)
cv2.createTrackbar("L-S", "Calibracion", 0, 255, nothing)
cv2.createTrackbar("L-V", "Calibracion", 100, 255, nothing) # Empezamos en 100 para blanco oscuro
cv2.createTrackbar("U-H", "Calibracion", 180, 180, nothing)
cv2.createTrackbar("U-S", "Calibracion", 60, 255, nothing)
cv2.createTrackbar("U-V", "Calibracion", 255, 255, nothing)

cap = cv2.VideoCapture(VIDEO_PATH)

print("TECLAS:")
print("'q': Salir")
print("'p': Pausar / Reanudar")
print("'r': Reiniciar vídeo")

pausa = False

while True:
    if not pausa:
        ret, frame = cap.read()
        if not ret:
            # Reiniciar vídeo automáticamente al llegar al final
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue

    # 1. Procesamiento
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    # 2. Leer valores de las barras
    l_h = cv2.getTrackbarPos("L-H", "Calibracion")
    l_s = cv2.getTrackbarPos("L-S", "Calibracion")
    l_v = cv2.getTrackbarPos("L-V", "Calibracion")
    u_h = cv2.getTrackbarPos("U-H", "Calibracion")
    u_s = cv2.getTrackbarPos("U-S", "Calibracion")
    u_v = cv2.getTrackbarPos("U-V", "Calibracion")

    lower = np.array([l_h, l_s, l_v])
    upper = np.array([u_h, u_s, u_v])

    # 3. Crear máscara
    mask = cv2.inRange(hsv, lower, upper)
    # Limpiar ruido
    mask = cv2.medianBlur(mask, 5)
    
    # Mostrar resultados
    cv2.imshow("Mascara (Blanco = Detectado)", mask)
    cv2.imshow("Video Original", frame)

    key = cv2.waitKey(30) & 0xFF
    if key == ord('q'): break
    if key == ord('p'): pausa = not pausa
    if key == ord('r'): cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

cap.release()
cv2.destroyAllWindows()