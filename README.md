# Hand Pose Estimation for Hand Bionics

Sistem kontrol tangan bionik (prosthetic-style hand) berbasis estimasi pose tangan secara real-time. Tangan robot hasil 3D print dengan 5 jari tendon driven digerakkan oleh 5 micro servo (1 servo per jari) dan dikontrol oleh Arduino Uno. Pose tangan pengguna diestimasi lewat kamera menggunakan Python (OpenCV + MediaPipe Hand Landmarker) sudut tiap sendi jari dihitung dari titik landmark, diubah jadi target posisi servo, lalu dikirim ke Arduino secara real-time sehingga tangan bionik **meniru pose tangan asli** di depan kamera.

## Fitur

- Estimasi pose tangan real-time via webcam (21 titik landmark MediaPipe)
- Perhitungan sudut fleksi tiap sendi jari, dikonversi jadi persentase tekuk (curl)
- Smoothing adaptif, noise kecil diredam, gerakan asli tetap responsif tanpa lag
- Kontrol manual lewat Serial Monitor (gesture preset: buka, kepal, pinch, thumbs up, wave)
- Kalibrasi sudut servo per jari lewat perintah serial

## Hardware yang Dipakai

- 1x Arduino Uno
- 5x micro servo (SG90 / MG90S)
- Tangan robot 3D print (tendon driven, 5 jari)
- Catu daya eksternal 5V, minimal 2A (terpisah dari power Arduino)
- Kabel jumper secukupnya

## Wiring

| Jari | Pin Sinyal Arduino | Kabel V+ (merah) | Kabel GND (hitam/coklat) |
|------|--------------------|--------------------|--------------------------|
| Jempol | D3 | Catu daya 5V eksternal | GND bersama |
| Telunjuk | D5 | Catu daya 5V eksternal | GND bersama |
| Tengah | D6 | Catu daya 5V eksternal | GND bersama |
| Manis | D9 | Catu daya 5V eksternal | GND bersama |
| Kelingking | D10 | Catu daya 5V eksternal | GND bersama |

**Penting:** GND catu daya eksternal, GND Arduino, dan GND semua servo harus disatukan di satu titik yang sama (common ground). Jangan sambungkan kabel V+ servo ke pin 5V Arduino — 5 servo yang gerak bersamaan bisa menarik arus di atas kemampuan regulator Arduino.

## Software yang Dibutuhkan

- Arduino IDE
- Python 3.9 - 3.13
- Dependensi Python: `opencv-python`, `mediapipe`, `numpy`, `pyserial` (lihat `requirements.txt`)

## Instalasi

1. Clone repo ini:
   ```bash
   git clone https://github.com/USERNAME/hand-pose-estimation-for-hand-bionics.git
   cd hand-pose-estimation-for-hand-bionics
   ```
2. Install dependensi Python:
   ```bash
   pip install -r requirements.txt
   ```
3. Upload `tangan_robot_5servo.ino` ke Arduino Uno lewat Arduino IDE.

## Kalibrasi

Sebelum dipakai, kalibrasi dulu tiap servo lewat Serial Monitor (baud 9600):

```
1:0      -> servo 1 (jempol) ke sudut 0 derajat
1:180    -> servo 1 (jempol) ke sudut 180 derajat
cal      -> tampilkan posisi sudut semua servo saat ini
```

Catat sudut mana yang membuat jari lurus penuh (OPEN) dan sudut mana yang membuat jari menekuk penuh (CLOSE) untuk tiap servo. Update nilai tersebut di array `OPEN_ANGLE[]` dan `CLOSE_ANGLE[]` pada `tangan_robot_5servo.ino`, lalu upload ulang.

## Cara Pakai

### Kontrol manual (Serial Monitor)

| Perintah | Fungsi |
|----------|--------|
| `o` | Buka semua jari |
| `c` | Kepal / tutup semua jari |
| `p` | Pinch (jempol + telunjuk) |
| `t` | Thumbs up |
| `w` | Demo lambaian tangan |
| `N:sudut` | Set servo ke-N (1-5) ke sudut tertentu |
| `cal` | Tampilkan posisi sudut semua servo |

### Kontrol via kamera (deteksi gerakan tangan)

```bash
python deteksi_tangan.py --port COM3
```

Ganti `COM3` dengan port Arduino di komputer kamu. Tutup Serial Monitor Arduino IDE dulu sebelum menjalankan skrip ini (port hanya bisa dipakai satu aplikasi).

Mode preview tanpa mengirim ke Arduino:
```bash
python deteksi_tangan.py --no-serial
```

Tuning responsivitas kalau gerakan kurang halus atau kurang responsif:
```bash
python deteksi_tangan.py --port COM3 --min-smoothing 0.15 --max-smoothing 1.0
```

Tekan `q` di jendela kamera untuk keluar.

## Struktur File

```
.
├── tangan_robot_5servo.ino   # Sketch Arduino (kontrol servo + parser serial)
├── deteksi_tangan.py         # Skrip Python (deteksi tangan via kamera)
├── requirements.txt          # Dependensi Python
└── README.md
```

## Troubleshooting

- **Error upload "programmer is not responding"** pastikan Serial Monitor/skrip Python tertutup, cek kabel USB, coba port USB langsung (bukan hub).
- **Error `mediapipe has no attribute 'solutions'`** versi mediapipe terbaru (>=1.0) sudah pindah ke Tasks API, gunakan `deteksi_tangan.py` versi ini yang sudah pakai `HandLandmarker`.
- **Servo geter-geter** biasanya karena noise deteksi kamera; sudah ditangani lewat smoothing adaptif, tapi bisa dituning lebih lanjut lewat `--min-smoothing`/`--max-smoothing`.
- **Gerakan jari terbalik** tukar nilai `OPEN_ANGLE` dan `CLOSE_ANGLE` untuk servo yang bersangkutan di file `.ino`.

## Lisensi

Bebas dipakai dan dimodifikasi untuk keperluan belajar/non-komersial. Sebutkan sumber kalau di-fork atau dipakai ulang.
