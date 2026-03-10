from camera_picamera2 import PiCamera2Source
import cv2
import csv
import time
import os
import numpy as np

# ArUco settings 
ARUCO_DICT_ID     = cv2.aruco.DICT_4X4_50
MIN_SIDE_PX       = 10
DETECTION_LOG     = "detections.csv"
WRITE_COOLDOWN_MS = 1000
DEBUG_IMAGE_PATH  = "aruco_debug.jpg"
SAVE_EVERY_SEC    = 2.0
LOG_EVERY_SEC     = 2.0

# labels 
ARUCO_LABELS = {
    0:  "zone_de_decollage",
    1:  "robot",
    2:  "align",
    3:  "align",
    4:  "fenetre_facile_recto_droite_bas",
    5:  "fenetre_facile_recto_droite_haut",
    6:  "fenetre_facile_recto_gauche_haut",
    7:  "fenetre_facile_recto_gauche_bas",
    8:  "fenetre_facile_verso_droite_bas",
    9:  "fenetre_facile_verso_droite_haut",
    10: "fenetre_facile_verso_gauche_haut",
    11: "fenetre_facile_verso_gauche_bas",
    12: "fenetre_difficile_recto_bas",
    13: "fenetre_difficile_recto_haut",
    14: "fenetre_difficile_verso_bas",
    15: "fenetre_difficile_verso_haut",
}

#  Helpers 
def now_ms() -> int:
    return int(time.time() * 1000)

def preprocess(gray: np.ndarray) -> np.ndarray:
    """CLAHE adaptive contrast enhancement for variable lighting."""
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    return clahe.apply(gray)

def make_detector() -> cv2.aruco.ArucoDetector:
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT_ID)
    params = cv2.aruco.DetectorParameters()

    # Adaptive threshold range - handles bright/dark scenes
    params.adaptiveThreshWinSizeMin  = 3
    params.adaptiveThreshWinSizeMax  = 53
    params.adaptiveThreshWinSizeStep = 10
    params.adaptiveThreshConstant    = 7

    # Allow smaller markers (useful when drone is higher)
    params.minMarkerPerimeterRate      = 0.02
    params.polygonalApproxAccuracyRate = 0.05

    return cv2.aruco.ArucoDetector(aruco_dict, params)

def marker_min_side(corner) -> float:
    pts   = corner[0]
    sides = [float(cv2.norm(pts[i] - pts[(i + 1) % 4])) for i in range(4)]
    return min(sides)

def center_of(corner):
    pts = corner[0]
    return round(float(pts[:, 0].mean()), 1), round(float(pts[:, 1].mean()), 1)

def init_csv(path):
    exists = os.path.isfile(path)
    f      = open(path, "a", newline="")
    writer = csv.writer(f)
    if not exists:
        writer.writerow(["timestamp_ms", "id", "label", "cx", "cy"])
        f.flush()
    return f, writer

# Main 
def main():
    camera = PiCamera2Source(size=(1280, 720))
    camera.open()

    detector         = make_detector()
    csv_file, writer = init_csv(DETECTION_LOG)
    last_written     = {}
    last_save        = 0.0
    last_log         = 0.0

    print("[INFO] Starting detection loop... Press Ctrl+C to stop.")

    try:
        while True:
            ret, frame = camera.read()
            if not ret or frame is None:
                print("[WARNING] Failed to read frame.")
                time.sleep(0.05)
                continue

            t0 = time.perf_counter()

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = preprocess(gray)
            corners, ids, _ = detector.detectMarkers(gray)

            detect_ms = (time.perf_counter() - t0) * 1000.0
            ts  = now_ms()
            now = time.time()

            vis            = frame.copy()
            detected_info  = []

            if ids is not None and len(corners) > 0:
                cv2.aruco.drawDetectedMarkers(vis, corners, ids)

                for corner, marker_id in zip(corners, ids.flatten()):
                    if marker_min_side(corner) < MIN_SIDE_PX:
                        continue

                    label = ARUCO_LABELS.get(int(marker_id), f"unknown_{marker_id}")
                    cx, cy = center_of(corner)
                    detected_info.append((int(marker_id), label, cx, cy))

                    last_ts = last_written.get(marker_id, 0)
                    if ts - last_ts >= WRITE_COOLDOWN_MS:
                        writer.writerow([ts, marker_id, label, cx, cy])
                        csv_file.flush()
                        last_written[marker_id] = ts

            # Terminal log 
            if now - last_log >= LOG_EVERY_SEC:
                last_log = now
                print(f"\n[{time.strftime('%H:%M:%S')}] detect={detect_ms:.1f}ms")
                if detected_info:
                    for mid, label, cx, cy in detected_info:
                        print(f"  ID={mid:>2}  label={label:<40}  center=({cx},{cy})")
                else:
                    print("  No markers detected.")

            #  Save debug image 
            if now - last_save >= SAVE_EVERY_SEC:
                last_save = now
                cv2.imwrite(DEBUG_IMAGE_PATH, vis)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")

    finally:
        camera.release()
        csv_file.close()
        print(f"[INFO] Camera released. Detections saved to {DETECTION_LOG}")


if __name__ == "__main__":
    main()