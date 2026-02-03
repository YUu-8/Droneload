import time
import cv2

class HeadlessOutput:
    def __init__(self, save_path="aruco_debug.jpg", save_every_sec=1.0, log_every_sec=1.0):
        self.save_path = save_path
        self.save_every_sec = save_every_sec
        self.log_every_sec = log_every_sec
        self._last_save = 0.0
        self._last_log = 0.0

    def tick(self, vis_bgr, ids, detect_ms=None, latency_ms=None):
        now = time.time()

        if now - self._last_log >= self.log_every_sec:
            self._last_log = now
            if ids is None:
                print(f"[INFO] no markers | detect_ms={detect_ms} | latency_ms={latency_ms}")
            else:
                print(f"[INFO] ids={ids.flatten().tolist()} | detect_ms={detect_ms} | latency_ms={latency_ms}")

        if now - self._last_save >= self.save_every_sec:
            self._last_save = now
            cv2.imwrite(self.save_path, vis_bgr)
            print(f"[INFO] wrote {self.save_path} (scp it to view)")
