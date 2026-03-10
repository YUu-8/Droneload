#!/bin/bash
# setup.sh - RubikPi ArUco detection environment setup

echo "[1/4] Installing GStreamer..."
sudo apt update
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly

echo "[2/4] Installing numpy(about opencv,its will be built in build_openCV.sh)..."
sudo apt install -y python3-numpy

echo "[3/4] Installing RubikPi qtiqmmfsrc plugin..."
cd ~
git clone -b ubuntu_setup --single-branch https://github.com/rubikpi-ai/rubikpi-script.git
cd rubikpi-script
./install_ppa_pkgs.sh
cd ~

echo "[4/4] Verifying..."
python3 -c "import cv2; print('OpenCV:', cv2.__version__); print('aruco OK:', hasattr(cv2, 'aruco'))"

GSTREAMER=$(python3 -c "
import cv2
info = cv2.getBuildInformation()
idx = info.find('GStreamer')
print('YES' if idx != -1 and 'YES' in info[idx:idx+20] else 'NO')
")
echo "GStreamer in OpenCV: $GSTREAMER"

if [ "$GSTREAMER" = "NO" ]; then
    echo "[WARNING] OpenCV has no GStreamer support - CSI camera will NOT work."
    echo "[WARNING] Try manually: sudo apt install -y libopencv-dev python3-opencv"
else
    echo "[OK] GStreamer supported - CSI camera should work."
fi

if ! gst-inspect-1.0 qtiqmmfsrc > /dev/null 2>&1; then
    echo "[WARNING] qtiqmmfsrc not found - CSI camera may not work."
else
    echo "[OK] qtiqmmfsrc found."
fi