# camera_rubikpi_csi.py
import cv2
import numpy as np

class RubikPiCSICamera:
    def __init__(self, camera=0, size=(1280, 720), fps=30):
        self.camera = camera  # 0 = CAM1, 1 = CAM2
        self.size   = size
        self.fps    = fps
        self.cap    = None

    def _gstreamer_pipeline(self) -> str:
        w, h = self.size
        return (
            f"qtiqmmfsrc camera={self.camera} ! "
            f"video/x-raw,format=NV12,width={w},height={h},framerate={self.fps}/1 ! "
            f"videoconvert ! "
            f"video/x-raw,format=BGR ! "
            f"appsink drop=true max-buffers=1 sync=false"
        )

    def open(self) -> bool:
        pipeline = self._gstreamer_pipeline()
        self.cap  = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
        if not self.cap.isOpened():
            print(f"[ERROR] Failed to open CSI camera {self.camera}")
            print(f"[ERROR] Pipeline: {pipeline}")
            return False
        print(f"[INFO] CSI camera {self.camera} opened at {self.size[0]}x{self.size[1]}@{self.fps}fps")
        return True

    def read(self):
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None