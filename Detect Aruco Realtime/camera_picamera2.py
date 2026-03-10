import cv2
from picamera2 import Picamera2

class PiCamera2Source:
    def __init__(self, size=(1280, 720), format="RGB888"):
        self.size   = size
        self.format = format
        self.picam2 = None

    def open(self):
        self.picam2 = Picamera2()
        config = self.picam2.create_preview_configuration(
            main={"size": self.size, "format": self.format}
        )
        self.picam2.configure(config)
        self.picam2.start()

        # Reduce motion blur + compensate with gain
        self.picam2.set_controls({
            "ExposureTime": 5000,   
            "AnalogueGain": 4.0     
        })
        return True

    def read(self):
        if self.picam2 is None:
            return False, None
        frame_rgb = self.picam2.capture_array()
        frame_bgr = cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR)
        return True, frame_bgr

    def release(self):
        if self.picam2 is not None:
            self.picam2.stop()
            self.picam2 = None