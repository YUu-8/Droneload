import cv2
import numpy as np
import threading
import time
import os
import csv
from collections import deque
from picamera2 import Picamera2

# -------------------------
# settings (Raspberry Pi only)
# -------------------------
CAP_WIDTH = 1280
CAP_HEIGHT = 720
PICAM_FORMAT = "RGB888"  

ARUCO_DICT = cv2.aruco.DICT_4X4_50
DETECT_FPS = 12
QUEUE_MAXLEN = 1
MIN_SIDE_PX = 25
ENABLE_SUBPIX = True

DETECTION_LOG = "detections.csv"
WRITE_COOLDOWN_MS = 1000  
last_written = {}

# logger thread
LOG_QUEUE_MAXLEN = 5000

# headless debug output 
SAVE_DEBUG_IMAGE = True
DEBUG_IMAGE_PATH = "aruco_debug.jpg"
SAVE_EVERY_SEC = 1.0
LOG_EVERY_SEC = 1.0
STALE_MS = 300

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
# helpers
def polygon_side_lengths(corners_4x2: np.ndarray) -> np.ndarray:
    d = []
    for i in range(4):
        p1 = corners_4x2[i]
        p2 = corners_4x2[(i + 1) % 4]
        d.append(np.linalg.norm(p1 - p2))
    return np.array(d, dtype=np.float32)

def now_ms() -> int:
    return int(time.time() * 1000)

# shared state
frame_queue = deque(maxlen=QUEUE_MAXLEN)
queue_lock = threading.Lock()

result_lock = threading.Lock()
latest = {
    "ts_ms": 0,
    "ids": None,
    "corners": None,
    "quality": None,
    "detect_ms": 0
}

