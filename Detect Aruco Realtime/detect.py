import cv2
import numpy as np
import threading
import time
import os
import csv
from collections import deque

# -------------------------
# settings
# -------------------------
CAM_INDEX = 0
CAP_WIDTH = 1280
CAP_HEIGHT = 720

ARUCO_DICT = cv2.aruco.DICT_4X4_50
DETECT_FPS = 12
QUEUE_MAXLEN = 1
MIN_SIDE_PX = 25
ENABLE_SUBPIX = True
DETECTION_LOG = "detections.csv"
WRITE_COOLDOWN_MS = 1000
last_written = {}

# ArUco ID -> labels
ARUCO_LABELS = {
    0: "zone_de_decollage",
    1: "robot",
    2: "align",
    3: "align",
    4: "fenetre_facile_recto_droite_bas",
    5: "fenetre_facile_recto_droite_haut",
    6: "fenetre_facile_recto_gauche_haut",
    7: "fenetre_facile_recto_gauche_bas",
    8: "fenetre_facile_verso_droite_bas",
    9: "fenetre_facile_verso_droite_haut",
    10: "fenetre_facile_verso_gauche_haut",
    11: "fenetre_facile_verso_gauche_bas",
    12: "fenetre_difficile_recto_bas",
    13: "fenetre_difficile_recto_haut",
    14: "fenetre_difficile_verso_bas",
    15: "fenetre_difficile_verso_haut",
}
# functions
def polygon_side_lengths(corners_4x2: np.ndarray) -> np.ndarray:
    d = []
    for i in range(4):
        p1 = corners_4x2[i]
        p2 = corners_4x2[(i + 1) % 4]
        d.append(np.linalg.norm(p1 - p2))
    return np.array(d, dtype=np.float32)

def now_ms() -> int:
    return int(time.time() * 1000)
# data structures
frame_queue = deque(maxlen=QUEUE_MAXLEN)
queue_lock = threading.Lock()
result_lock = threading.Lock()
latest = {
    "ts_ms": 0,
    "ids": None,
    "corners": None,
    "quality": None,   # list of dicts per marker
    "detect_ms": 0
}

stop_event = threading.Event()

# -------------------------
# read caputure thread
# -------------------------
def capture_loop():
    cap = cv2.VideoCapture(CAM_INDEX)
    if not cap.isOpened():
        print("ERROR: Cannot open camera.")
        stop_event.set()
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAP_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAP_HEIGHT)

    while not stop_event.is_set():
        ok, frame = cap.read()
        if not ok:
            print("ERROR: Frame grab failed.")
            stop_event.set()
            break

        ts = now_ms()
        with queue_lock:
            frame_queue.append((ts, frame))

    cap.release()
# detect thread
def detect_loop():
    aruco_dict = cv2.aruco.getPredefinedDictionary(ARUCO_DICT)
    params = cv2.aruco.DetectorParameters()
    detector = cv2.aruco.ArucoDetector(aruco_dict, params)

    period = 1.0 / max(DETECT_FPS, 1)
    last_run = 0.0

    while not stop_event.is_set():
        t = time.time()
        if t - last_run < period:
            time.sleep(0.001)
            continue
        last_run = t

        with queue_lock:
            if len(frame_queue) == 0:
                continue
            ts, frame = frame_queue[-1]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        t0 = time.time()
        corners, ids, _rejected = detector.detectMarkers(gray)
        # some OpenCV builds return corners as an immutable tuple — convert to list
        if corners is not None:
            corners = list(corners)
        detect_ms = int((time.time() - t0) * 1000)

        quality = []
        if ids is not None and len(ids) > 0 and ENABLE_SUBPIX:
            term = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.01)
            for i in range(len(corners)):
                c = corners[i].reshape(4, 2).astype(np.float32)
                cv2.cornerSubPix(gray, c, winSize=(3, 3), zeroZone=(-1, -1), criteria=term)
                corners[i] = c.reshape(1, 4, 2)

        if ids is not None and len(ids) > 0:
            for i in range(len(ids)):
                c = corners[i].reshape(4, 2)
                sides = polygon_side_lengths(c)
                min_side = float(np.min(sides))
                passed = min_side >= MIN_SIDE_PX
                quality.append({"min_side_px": min_side, "pass": passed})

        with result_lock:
            latest["ts_ms"] = ts
            latest["ids"] = ids
            latest["corners"] = corners
            latest["quality"] = quality
            latest["detect_ms"] = detect_ms

    
        if ids is not None and corners is not None and quality:
            for i in range(len(ids)):
                q = quality[i] if i < len(quality) else {"pass": False}
                if not q.get("pass", False):
                    continue

                try:
                    id_val = int(np.array(ids).flatten()[i])
                except Exception:
                    try:
                        id_val = int(ids[i])
                    except Exception:
                        continue

                now = now_ms()
                last = last_written.get(id_val, 0)
                if now - last < WRITE_COOLDOWN_MS:
                    continue

                # calculate center
                try:
                    pts = corners[i].reshape(4, 2)
                    cx, cy = float(pts[:, 0].mean()), float(pts[:, 1].mean())
                except Exception:
                    cx, cy = -1.0, -1.0

                label = ARUCO_LABELS.get(id_val, str(id_val))

                # confirm header
                write_header = not os.path.exists(DETECTION_LOG)
                try:
                    with open(DETECTION_LOG, "a", newline='', encoding='utf-8') as f:
                        writer = csv.writer(f)
                        if write_header:
                            writer.writerow(["id", "label", "min_side_px", "center_x", "center_y"])
                        writer.writerow([id_val, label, f"{q.get('min_side_px', -1):.2f}", f"{cx:.2f}", f"{cy:.2f}"])
                    last_written[id_val] = now
                except Exception as e:
                    print(f"[WARN] failed to write log: {e}")

# main loop: visualization and UI
def main():
    t_cap = threading.Thread(target=capture_loop, daemon=True)
    t_det = threading.Thread(target=detect_loop, daemon=True)
    t_cap.start()
    t_det.start()

    last_log = time.time()

    while not stop_event.is_set():
        with queue_lock:
            if len(frame_queue) == 0:
                time.sleep(0.01)
                continue
            ts, frame = frame_queue[-1]
        vis = frame.copy()

        with result_lock:
            ids = latest["ids"]
            corners = latest["corners"]
            quality = latest["quality"]
            detect_ms = latest["detect_ms"]
            det_ts = latest["ts_ms"]

        # ids from detectMarkers can be an array with shape (N,1); flatten to 1D
        if ids is not None:
            try:
                ids = np.array(ids).flatten()
            except Exception:
                pass

        # add hoc latency info
        latency_ms = now_ms() - det_ts if det_ts else -1
        cv2.putText(vis, f"Detect: {detect_ms} ms  TargetFPS: {DETECT_FPS}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (240, 240, 240), 2)
        cv2.putText(vis, f"Pipeline latency: {latency_ms} ms  (queue maxlen={QUEUE_MAXLEN})",
                    (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (240, 240, 240), 2)

        if ids is not None and corners is not None:
            for i in range(len(ids)):
                passed = True
                if quality and i < len(quality):
                    passed = quality[i].get("pass", True)

                if not passed:
                    continue

                cv2.aruco.drawDetectedMarkers(vis, [corners[i]], ids[i:i+1])

                pts = corners[i].reshape(4, 2)
                center = pts.mean(axis=0).astype(int)
                cv2.circle(vis, tuple(center), 4, (0, 255, 0), -1)

                # overlay min_side_px
                ms = quality[i]["min_side_px"] if quality and i < len(quality) else -1
                # ensure id and ms are plain Python scalars to avoid numpy->scalar deprecation
                id_val = int(ids[i]) if ids is not None else -1
                ms_val = float(ms)
                cv2.putText(vis, f"id={id_val} minSide={ms_val:.1f}px",
                            (center[0] + 6, center[1] - 6),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        if time.time() - last_log > 1.0:
            last_log = time.time()
            if ids is None:
                print(f"[INFO] no markers | detect_ms={detect_ms} | latency_ms={latency_ms}")
            else:
                print(f"[INFO] ids={ids.flatten().tolist()} | detect_ms={detect_ms} | latency_ms={latency_ms} | quality={quality}")

        cv2.imshow("ArUco Realtime (DICT_4X4_50)", vis)
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord("q"):
            stop_event.set()
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
    print("[INFO] program ended")