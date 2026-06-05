import cv2

# Resolución de captura — full FOV del IMX219
CAP_W, CAP_H = 1640, 1232
# Resolución de display (ventana)
OUT_W, OUT_H = 640, 480

WIN = "Calibracion FOV  |  G=guias  Q=salir+imprimir"


def open_camera():
    try:
        from picamera2 import Picamera2
        cam = Picamera2()
        cam.configure(cam.create_video_configuration(
            main={"size": (CAP_W, CAP_H), "format": "BGR888"}
        ))
        cam.start()
        class _Src:
            def read(self):    return True, cam.capture_array("main")
            def release(self): cam.stop()
        print(f"[CAL] PiCamera2 OK  —  capturando a {CAP_W}x{CAP_H} (full FOV)")
        return _Src()
    except Exception:
        cap = cv2.VideoCapture(0)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAP_W)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_H)
        print("[CAL] Webcam OK")
        return cap


def main():
    cam = open_camera()
    cv2.namedWindow(WIN, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WIN, OUT_W, OUT_H + 100)

    # SCALE: 10–100 (porcentaje del frame completo que se usa)
    cv2.createTrackbar("SCALE %", WIN, 100, 100, lambda v: None)

    show_guides = True
    final_scale = 100

    while True:
        ok, frame = cam.read()
        if not ok:
            break

        scale = max(10, cv2.getTrackbarPos("SCALE %", WIN))
        final_scale = scale

        # Recorte centrado según el scale
        cw = int(CAP_W * scale / 100)
        ch = int(CAP_H * scale / 100)
        x1 = (CAP_W - cw) // 2
        y1 = (CAP_H - ch) // 2
        display = cv2.resize(frame[y1:y1+ch, x1:x1+cw], (OUT_W, OUT_H))

        if show_guides:
            m = 4
            cv2.rectangle(display, (m, m), (OUT_W-m, OUT_H-m), (0, 255, 0), 2)
            cv2.line(display, (OUT_W//2, 0), (OUT_W//2, OUT_H), (0, 255, 0), 1)
            cv2.line(display, (0, OUT_H//2), (OUT_W, OUT_H//2), (0, 255, 0), 1)

        info = f"SCALE: {scale}%   crop: {cw}x{ch} -> {OUT_W}x{OUT_H}"
        cv2.putText(display, info, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0,0,0), 3, cv2.LINE_AA)
        cv2.putText(display, info, (10, 28), cv2.FONT_HERSHEY_SIMPLEX,
                    0.55, (0,255,180), 1, cv2.LINE_AA)

        cv2.imshow(WIN, display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('g'):
            show_guides = not show_guides
        elif key == ord('q'):
            break

    cam.release()
    cv2.destroyAllWindows()

    cw = int(CAP_W * final_scale / 100)
    ch = int(CAP_H * final_scale / 100)

    print("\n══════════════════════════════════════")
    print("  Valores finales de calibración      ")
    print("══════════════════════════════════════")
    print(f"  SCALE  = {final_scale}%")
    print(f"  CAP_W  = {CAP_W}")
    print(f"  CAP_H  = {CAP_H}")
    print(f"  CROP_W = {cw}")
    print(f"  CROP_H = {ch}")
    print("══════════════════════════════════════")
    print("  Pásame estos valores y te digo      ")
    print("  qué cambiar en config.py            ")
    print("══════════════════════════════════════\n")


if __name__ == "__main__":
    main()
