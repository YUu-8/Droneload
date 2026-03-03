from camera_picamera2 import PiCamera2Source
from headless_output import HeadlessOutput
import cv2
import time

def detect_aruco_markers(frame, aruco_dict, parameters):
    """
    detect ArUco markers
    """
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    corners, ids, _ = cv2.aruco.detectMarkers(gray, aruco_dict, parameters=parameters)
    return corners, ids

def main():
    # initialize camera
    camera = PiCamera2Source(size=(1280, 720))
    if not camera.open():
        print("[ERROR] Failed to open camera.")
        return

    # initialize headless output
    output = HeadlessOutput(save_path="aruco_debug.jpg", save_every_sec=2.0, log_every_sec=2.0)

    # initialize ArUco detector
    aruco_dict = cv2.aruco.Dictionary_get(cv2.aruco.DICT_4X4_50)
    parameters = cv2.aruco.DetectorParameters_create()

    try:
        print("[INFO] Starting detection loop...")
        for _ in range(10):  
            ret, frame = camera.read()
            if not ret:
                print("[WARNING] Failed to read frame.")
                continue

            
            corners, ids = detect_aruco_markers(frame, aruco_dict, parameters)

        
            detect_time = 50  # ms
            latency_time = 10  # ms

            output.tick(frame, ids, detect_ms=detect_time, latency_ms=latency_time)

            time.sleep(0.5)  

    finally:
        camera.release()
        print("[INFO] Camera released.")

if __name__ == "__main__":
    main()