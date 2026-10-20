/*
  =========================================================
  TANGAN ROBOT 5 SERVO - Arduino Uno
  =========================================================
  Kontrol 5 jari (1 servo per jari) menggunakan 5x micro servo
  (SG90 / MG90S).

  WIRING:
    Servo 1 - D3   -> jempol
    Servo 2 - D5   -> telunjuk
    Servo 3 - D6   -> tengah
    Servo 4 - D9   -> manis
    Servo 5 - D10  -> kelingking

    Semua kabel merah (V+) servo -> catu daya eksternal 5V (JANGAN dari pin 5V Arduino)
    Semua kabel coklat/hitam (GND) servo -> GND catu daya eksternal DAN GND Arduino (disatukan)
    Semua kabel oranye/kuning (sinyal) servo -> pin D3,D5,D6,D9,D10 sesuai mapping di atas

  CATATAN PENTING:
    5 servo yang bergerak bersamaan bisa menarik arus 1.5-3A saat stall,
    di atas kemampuan regulator 5V Arduino (~500mA). WAJIB pakai
    catu daya eksternal 5V minimal 2A dengan GND disatukan ke Arduino.

  CARA PAKAI (via Serial Monitor, baud 9600):
    o          -> buka semua jari (open hand)
    c          -> kepal / tutup semua jari (close/fist)
    p          -> gerakan pinch (jempol + telunjuk)
    t          -> thumbs up
    w          -> lambaikan tangan (wave, demo)
    1:90       -> set servo index 1 ke sudut 90 derajat (index 1-5)
    cal        -> tampilkan posisi sudut semua servo saat ini
    F:c0,c1,c2,c3,c4  -> batch dari script Python (persentase tekuk 0-100 per servo,
                          urutan: jempol, telunjuk, tengah, manis, kelingking)
  =========================================================
*/

#include <Servo.h>

const uint8_t NUM_SERVOS = 5;
const uint8_t SERVO_PINS[NUM_SERVOS] = {3, 5, 6, 9, 10};

const char* SERVO_NAMES[NUM_SERVOS] = {
  "Jempol",
  "Telunjuk",
  "Tengah",
  "Manis",
  "Kelingking"
};

// ---------- Kalibrasi posisi ----------
// Sesuaikan nilai ini dengan mekanisme tendon fisik kamu.
// OPEN  = posisi jari lurus/terbuka
// CLOSE = posisi jari menekuk/mengepal
// Jika arah gerak terbalik, tukar nilai OPEN & CLOSE untuk servo itu.
const int OPEN_ANGLE[NUM_SERVOS]  = {0,   130, 130, 130, 130};
const int CLOSE_ANGLE[NUM_SERVOS] = {130, 0,   0,   0,   0};

Servo myServo[NUM_SERVOS];
int currentAngle[NUM_SERVOS];

const int MOVE_STEP_DELAY = 15; // ms antar langkah untuk gerakan halus

void setup() {
  Serial.begin(9600);
  Serial.println(F("=== Tangan Robot 5 Servo siap ==="));
  Serial.println(F("Perintah: o=buka c=kepal p=pinch t=thumbsup w=wave  N:sudut  cal  F:c0,..,c4"));

  for (uint8_t i = 0; i < NUM_SERVOS; i++) {
    myServo[i].attach(SERVO_PINS[i]);
    currentAngle[i] = OPEN_ANGLE[i];
    myServo[i].write(currentAngle[i]);
  }
  delay(500);
}

void loop() {
  if (Serial.available() > 0) {
    String cmd = Serial.readStringUntil('\n');
    cmd.trim();
    handleCommand(cmd);
  }
}

void moveServoSmooth(uint8_t index, int targetAngle) {
  targetAngle = constrain(targetAngle, 0, 180);
  int step = (targetAngle > currentAngle[index]) ? 1 : -1;
  while (currentAngle[index] != targetAngle) {
    currentAngle[index] += step;
    myServo[index].write(currentAngle[index]);
    delay(MOVE_STEP_DELAY);
  }
}

void moveAllSmooth(const int targets[NUM_SERVOS]) {
  bool done = false;
  int target[NUM_SERVOS];
  for (uint8_t i = 0; i < NUM_SERVOS; i++) target[i] = constrain(targets[i], 0, 180);

  while (!done) {
    done = true;
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
      if (currentAngle[i] != target[i]) {
        currentAngle[i] += (target[i] > currentAngle[i]) ? 1 : -1;
        myServo[i].write(currentAngle[i]);
        done = false;
      }
    }
    delay(MOVE_STEP_DELAY);
  }
}

void openHand() {
  int targets[NUM_SERVOS];
  for (uint8_t i = 0; i < NUM_SERVOS; i++) targets[i] = OPEN_ANGLE[i];
  moveAllSmooth(targets);
  Serial.println(F("Tangan terbuka"));
}

void closeHand() {
  int targets[NUM_SERVOS];
  for (uint8_t i = 0; i < NUM_SERVOS; i++) targets[i] = CLOSE_ANGLE[i];
  moveAllSmooth(targets);
  Serial.println(F("Tangan mengepal"));
}

void pinchGesture() {
  int targets[NUM_SERVOS];
  for (uint8_t i = 0; i < NUM_SERVOS; i++) targets[i] = OPEN_ANGLE[i];
  targets[0] = CLOSE_ANGLE[0]; // jempol
  targets[1] = CLOSE_ANGLE[1]; // telunjuk
  moveAllSmooth(targets);
  Serial.println(F("Pinch: jempol + telunjuk"));
}

void thumbsUpGesture() {
  int targets[NUM_SERVOS];
  targets[0] = OPEN_ANGLE[0]; // jempol tetap lurus
  for (uint8_t i = 1; i < NUM_SERVOS; i++) targets[i] = CLOSE_ANGLE[i]; // 4 jari lain kepal
  moveAllSmooth(targets);
  Serial.println(F("Thumbs up"));
}

void waveDemo() {
  Serial.println(F("Wave demo..."));
  for (uint8_t loopCount = 0; loopCount < 3; loopCount++) {
    openHand();
    delay(200);
    closeHand();
    delay(200);
  }
  openHand();
}

void handleCommand(String cmd) {
  if (cmd.length() == 0) return;

  if (cmd.equalsIgnoreCase("o")) {
    openHand();
  } else if (cmd.equalsIgnoreCase("c")) {
    closeHand();
  } else if (cmd.equalsIgnoreCase("p")) {
    pinchGesture();
  } else if (cmd.equalsIgnoreCase("t")) {
    thumbsUpGesture();
  } else if (cmd.equalsIgnoreCase("w")) {
    waveDemo();
  } else if (cmd.equalsIgnoreCase("cal")) {
    for (uint8_t i = 0; i < NUM_SERVOS; i++) {
      Serial.print(SERVO_NAMES[i]);
      Serial.print(F(" (pin "));
      Serial.print(SERVO_PINS[i]);
      Serial.print(F(") = "));
      Serial.println(currentAngle[i]);
    }
  } else if (cmd.startsWith("F:")) {
    String data = cmd.substring(2);
    int targets[NUM_SERVOS];
    uint8_t idx = 0;
    int start = 0;
    for (int i = 0; i <= (int)data.length() && idx < NUM_SERVOS; i++) {
      if (i == (int)data.length() || data.charAt(i) == ',') {
        int percent = constrain(data.substring(start, i).toInt(), 0, 100);
        targets[idx] = map(percent, 0, 100, OPEN_ANGLE[idx], CLOSE_ANGLE[idx]);
        idx++;
        start = i + 1;
      }
    }
    if (idx == NUM_SERVOS) {
      for (uint8_t i = 0; i < NUM_SERVOS; i++) {
        currentAngle[i] = constrain(targets[i], 0, 180);
        myServo[i].write(currentAngle[i]);
      }
    } else {
      Serial.println(F("Format F: salah, perlu 5 nilai dipisah koma"));
    }
  } else if (cmd.indexOf(':') > 0) {
    int sep = cmd.indexOf(':');
    int idx = cmd.substring(0, sep).toInt() - 1;
    int angle = cmd.substring(sep + 1).toInt();
    if (idx >= 0 && idx < NUM_SERVOS) {
      moveServoSmooth(idx, angle);
      Serial.print(SERVO_NAMES[idx]);
      Serial.print(F(" -> "));
      Serial.println(angle);
    } else {
      Serial.println(F("Index servo tidak valid (gunakan 1-5)"));
    }
  } else {
    Serial.println(F("Perintah tidak dikenal. Gunakan: o c p t w N:sudut cal F:c0,..,c4"));
  }
}
