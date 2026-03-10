# camera_rubikpi.py
import cv2

class RubikPiCamera:
    def __init__(self, device=0, size=(1280, 720)):
        self.device = device
        self.size   = size
        self.cap    = None

    def open(self):
        self.cap = cv2.VideoCapture(self.device)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH,  self.size[0])
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.size[1])
        self.cap.set(cv2.CAP_PROP_FPS, 30)
        return self.cap.isOpened()

    def read(self):
        if self.cap is None:
            return False, None
        return self.cap.read()

    def release(self):
        if self.cap is not None:
            self.cap.release()
            self.cap = None