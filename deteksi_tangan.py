"""
=========================================================
DETEKSI GERAKAN TANGAN VIA KAMERA -> KONTROL TANGAN ROBOT
(versi MediaPipe Tasks API, untuk mediapipe >= 1.0)
=========================================================
MediaPipe versi 1.0 ke atas menghapus API lama "mp.solutions.hands"
dan menggantinya dengan Tasks API (HandLandmarker). Skrip ini pakai
API baru tersebut. Kalau mediapipe di komputermu versi lama (0.10.x
ke bawah), skrip versi sebelumnya (yang pakai mp.solutions) masih
tetap jalan -- tapi kalau sudah kena error "no attribute solutions",
berarti kamu perlu skrip ini.

Cara kerja tetap sama: OpenCV ambil gambar kamera, MediaPipe deteksi
21 titik landmark tangan, dihitung persentase tekuk tiap jari, lalu
dikirim ke Arduino lewat serial dengan format:

    F:c0,c1,c2,c3,c4\n

Urutan c0..c4 harus SAMA dengan urutan SERVO_PINS di sketch Arduino:
    c0 = jempol
    c1 = telunjuk
    c2 = tengah
    c3 = manis
    c4 = kelingking

INSTALL DEPENDENSI:
    pip install opencv-python mediapipe numpy pyserial

Skrip ini akan otomatis download file model "hand_landmarker.task"
(sekitar 8 MB) dari server Google saat pertama kali dijalankan, jadi
butuh koneksi internet di percobaan pertama saja. Kalau auto-download
gagal (misal karena firewall kampus), unduh manual dari:
    https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task
lalu taruh filenya satu folder dengan skrip ini.

CARA PAKAI:
    python deteksi_tangan.py --port COM3
    python deteksi_tangan.py --no-serial      (mode preview saja)
    Tekan 'q' di jendela kamera untuk keluar.

KALAU MASIH GETER ATAU KURANG RESPONSIF:
    Skrip ini pakai smoothing ADAPTIF: gerakan kecil (noise diam) diredam
    kuat, gerakan besar (jari beneran gerak) diteruskan nyaris tanpa lag.
    - Masih geter pas diam -> turunkan --min-smoothing (misal 0.15)
    - Kurang responsif pas gerak cepat -> naikkan --max-smoothing (misal 1.0)
      atau turunkan --smoothing-range (misal 8)
    Contoh:
        python deteksi_tangan.py --port COM3 --min-smoothing 0.15 --max-smoothing 1.0
=========================================================
"""

import argparse
import os
import time
import urllib.request

import cv2
import numpy as np
import mediapipe as mp

try:
    import serial
except ImportError:
    serial = None


SERVO_NAMES = ["jempol", "telunjuk", "tengah", "manis", "kelingking"]

FINGER_LANDMARKS = {
    1: (5, 6, 8),     # telunjuk
    2: (9, 10, 12),   # tengah
    3: (13, 14, 16),  # manis
    4: (17, 18, 20),  # kelingking
}

HAND_CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (0, 9), (9, 10), (10, 11), (11, 12),
    (0, 13), (13, 14), (14, 15), (15, 16),
    (0, 17), (17, 18), (18, 19), (19, 20),
    (5, 9), (9, 13), (13, 17),
]

MODEL_PATH = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/latest/hand_landmarker.task"
)


def ensure_model():
    if os.path.exists(MODEL_PATH):
        return
    print(f"File model {MODEL_PATH} belum ada, mendownload dari Google...")
    try:
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH)
        print("Download model selesai.")
    except Exception as e:
        raise RuntimeError(
            f"Gagal download model otomatis ({e}).\n"
            f"Unduh manual dari:\n{MODEL_URL}\n"
            f"lalu taruh file hand_landmarker.task satu folder dengan skrip ini."
        )


def calc_angle(a, b, c):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    ba = a - b
    bc = c - b
    denom = (np.linalg.norm(ba) * np.linalg.norm(bc)) + 1e-6
    cosine = np.clip(np.dot(ba, bc) / denom, -1.0, 1.0)
    return np.degrees(np.arccos(cosine))


def angle_to_curl(angle, straight_angle, curled_angle):
    curl = (straight_angle - angle) / (straight_angle - curled_angle) * 100
    return float(np.clip(curl, 0, 100))


def compute_curls(landmarks):
    """landmarks: list 21 titik (x, y) ternormalisasi. Return list 5 float (0-100), belum di-smooth."""
    curls = [0] * 5

    for servo_idx, (mcp, pip_, tip) in FINGER_LANDMARKS.items():
        ang = calc_angle(landmarks[mcp], landmarks[pip_], landmarks[tip])
        curls[servo_idx] = angle_to_curl(ang, straight_angle=170, curled_angle=60)

    # Jempol (servo index 0): sudut di sendi IP (titik 2-3-4)
    thumb_ang = calc_angle(landmarks[2], landmarks[3], landmarks[4])
    curls[0] = angle_to_curl(thumb_ang, straight_angle=170, curled_angle=130)

    return curls


def adaptive_alpha(raw_curls, smoothed_curls, min_alpha, max_alpha, delta_range):
    """Alpha kecil (smoothing kuat) kalau perubahan kecil (noise diam),
    alpha besar (nyaris tanpa lag) kalau perubahan besar (gerakan asli)."""
    alphas = []
    for r, s in zip(raw_curls, smoothed_curls):
        delta = abs(r - s)
        t = min(delta / delta_range, 1.0)
        alphas.append(min_alpha + (max_alpha - min_alpha) * t)
    return alphas


def draw_landmarks(frame, points):
    for start, end in HAND_CONNECTIONS:
        cv2.line(frame, points[start], points[end], (0, 200, 0), 2)
    for x, y in points:
        cv2.circle(frame, (x, y), 4, (0, 255, 255), -1)


def main():
    parser = argparse.ArgumentParser(description="Deteksi gerakan tangan -> kontrol tangan robot")
    parser.add_argument("--port", default="COM3", help="Serial port Arduino (contoh: COM3, /dev/ttyUSB0)")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate (samakan dengan sketch Arduino)")
    parser.add_argument("--camera", type=int, default=0, help="Index kamera (0 = kamera default)")
    parser.add_argument("--send-hz", type=float, default=20.0, help="Maksimum frekuensi kirim ke Arduino per detik")
    parser.add_argument("--min-smoothing", type=float, default=0.25, help="Alpha minimum (dipakai saat gerakan kecil/diam, redam noise). Default 0.25")
    parser.add_argument("--max-smoothing", type=float, default=0.95, help="Alpha maksimum (dipakai saat gerakan besar, hampir tanpa lag). Default 0.95")
    parser.add_argument("--smoothing-range", type=float, default=12.0, help="Besar perubahan (persen) yang sudah dianggap gerakan asli, bukan noise. Default 12")
    parser.add_argument("--deadzone", type=float, default=1.5, help="Minimal perubahan persen sebelum dikirim ulang ke Arduino (default 1.5)")
    parser.add_argument("--no-serial", action="store_true", help="Mode preview saja, tanpa kirim ke Arduino")
    parser.add_argument("--mirror", action="store_true", default=True, help="Flip kamera secara horizontal (default aktif)")
    args = parser.parse_args()

    ensure_model()

    ser = None
    if not args.no_serial:
        if serial is None:
            print("pyserial belum terinstall. Jalankan: pip install pyserial")
            print("Lanjut mode preview tanpa kontrol servo.")
        else:
            try:
                ser = serial.Serial(args.port, args.baud, timeout=1)
                time.sleep(2)
                print(f"Terhubung ke Arduino di {args.port} @ {args.baud} baud")
            except Exception as e:
                print(f"Gagal buka serial port {args.port}: {e}")
                print("Lanjut mode preview tanpa kontrol servo. Cek nama port dan kabel USB.")

    BaseOptions = mp.tasks.BaseOptions
    HandLandmarker = mp.tasks.vision.HandLandmarker
    HandLandmarkerOptions = mp.tasks.vision.HandLandmarkerOptions
    VisionRunningMode = mp.tasks.vision.RunningMode

    options = HandLandmarkerOptions(
        base_options=BaseOptions(model_asset_path=MODEL_PATH),
        running_mode=VisionRunningMode.IMAGE,
        num_hands=1,
        min_hand_detection_confidence=0.6,
        min_hand_presence_confidence=0.5,
        min_tracking_confidence=0.5,
    )

    cap = cv2.VideoCapture(args.camera)
    if not cap.isOpened():
        print(f"Tidak bisa buka kamera index {args.camera}")
        return

    min_send_interval = 1.0 / max(args.send_hz, 1.0)
    last_send_time = 0.0
    last_sent_curls = None
    smoothed_curls = None

    print("Kamera aktif. Tekan 'q' untuk keluar.")

    with HandLandmarker.create_from_options(options) as landmarker:
        while True:
            ok, frame = cap.read()
            if not ok:
                print("Gagal ambil frame dari kamera.")
                break

            if args.mirror:
                frame = cv2.flip(frame, 1)

            h, w = frame.shape[:2]
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            result = landmarker.detect(mp_image)

            if result.hand_landmarks:
                hand_landmarks = result.hand_landmarks[0]
                landmarks_norm = [(lm.x, lm.y) for lm in hand_landmarks]
                points_px = [(int(x * w), int(y * h)) for (x, y) in landmarks_norm]

                draw_landmarks(frame, points_px)
                raw_curls = compute_curls(landmarks_norm)

                # Smoothing adaptif: redam kuat kalau perubahan kecil (noise diam),
                # nyaris tanpa lag kalau perubahan besar (gerakan asli)
                if smoothed_curls is None:
                    smoothed_curls = raw_curls
                else:
                    alphas = adaptive_alpha(
                        raw_curls, smoothed_curls,
                        args.min_smoothing, args.max_smoothing, args.smoothing_range,
                    )
                    smoothed_curls = [a * r + (1 - a) * s for a, r, s in zip(alphas, raw_curls, smoothed_curls)]

                curls = [int(round(c)) for c in smoothed_curls]

                label = " ".join(f"{name}:{val}" for name, val in zip(SERVO_NAMES, curls))
                cv2.putText(frame, label, (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 0), 1)

                now = time.time()
                if ser is not None and (now - last_send_time) >= min_send_interval:
                    changed = (
                        last_sent_curls is None
                        or any(abs(c - p) >= args.deadzone for c, p in zip(curls, last_sent_curls))
                    )
                    if changed:
                        cmd = "F:" + ",".join(str(c) for c in curls) + "\n"
                        try:
                            ser.write(cmd.encode())
                        except Exception as e:
                            print(f"Gagal kirim ke serial: {e}")
                        last_sent_curls = curls
                        last_send_time = now
            else:
                cv2.putText(frame, "Tangan tidak terdeteksi", (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

            cv2.imshow("Deteksi Tangan (tekan q untuk keluar)", frame)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()
    if ser is not None:
        ser.close()


if __name__ == "__main__":
    main()
