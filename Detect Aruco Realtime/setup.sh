#!/bin/bash
# setup.sh - RubikPi ArUco detection environment setup

echo "[1/3] Installing GStreamer..."
sudo apt update
sudo apt install -y \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly

echo "[2/3] Installing Python packages..."
pip3 install opencv-contrib-python --break-system-packages

echo "[3/3] Installing RubikPi qtiqmmfsrc plugin..."
cd ~
git clone -b ubuntu_setup --single-branch https://github.com/rubikpi-ai/rubikpi-script.git
cd rubikpi-script
./install_ppa_pkgs.sh
cd ..

echo "[Done] Verifying..."
python3 -c "import cv2; print('OpenCV:', cv2.__version__)"
gst-inspect-1.0 qtiqmmfsrc | head -1