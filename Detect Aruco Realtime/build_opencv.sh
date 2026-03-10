#!/bin/bash
# build_opencv.sh - Build OpenCV with GStreamer + contrib (aruco) support
# Expected build time: 1-2 hours on RubikPi 3

set -e  # Exit on any error

OPENCV_VERSION="4.10.0"
BUILD_DIR="$HOME/opencv_build"

echo "================================================"
echo " OpenCV $OPENCV_VERSION build script for RubikPi"
echo "================================================"

# System dependencies for OpenCV with GStreamer and contrib modules
echo "[1/6] Installing system dependencies..."
sudo apt update
sudo apt install -y \
    build-essential cmake git pkg-config \
    python3-dev python3-numpy \
    libgstreamer1.0-dev \
    libgstreamer-plugins-base1.0-dev \
    libgstreamer-plugins-bad1.0-dev \
    gstreamer1.0-tools \
    gstreamer1.0-plugins-base \
    gstreamer1.0-plugins-good \
    gstreamer1.0-plugins-bad \
    gstreamer1.0-plugins-ugly \
    libjpeg-dev libpng-dev libtiff-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libv4l-dev v4l-utils \
    libgtk-3-dev \
    libatlas-base-dev gfortran \
    unzip wget

# Download sources 
echo "[2/6] Downloading OpenCV $OPENCV_VERSION sources..."
mkdir -p "$BUILD_DIR" && cd "$BUILD_DIR"

wget -q --show-progress -O opencv.zip \
    https://github.com/opencv/opencv/archive/refs/tags/${OPENCV_VERSION}.zip
wget -q --show-progress -O opencv_contrib.zip \
    https://github.com/opencv/opencv_contrib/archive/refs/tags/${OPENCV_VERSION}.zip

unzip -q opencv.zip
unzip -q opencv_contrib.zip

# Configure build 
echo "[3/6] Configuring build..."
cd "$BUILD_DIR/opencv-${OPENCV_VERSION}"
mkdir -p build && cd build

cmake \
    -D CMAKE_BUILD_TYPE=RELEASE \
    -D CMAKE_INSTALL_PREFIX=/usr/local \
    -D OPENCV_EXTRA_MODULES_PATH="$BUILD_DIR/opencv_contrib-${OPENCV_VERSION}/modules" \
    -D WITH_GSTREAMER=ON \
    -D WITH_V4L=ON \
    -D WITH_FFMPEG=ON \
    -D BUILD_opencv_python3=ON \
    -D PYTHON3_EXECUTABLE=$(which python3) \
    -D OPENCV_GENERATE_PKGCONFIG=ON \
    -D BUILD_EXAMPLES=OFF \
    -D BUILD_TESTS=OFF \
    -D BUILD_PERF_TESTS=OFF \
    -D OPENCV_ENABLE_NONFREE=ON \
    ..

# Verify GStreamer is enabled before building
echo "[CHECK] Verifying GStreamer is enabled in build config..."
if grep -q "GStreamer.*YES" CMakeCache.txt 2>/dev/null || \
   cmake --build . --target opencv_videoio -- -n 2>/dev/null | grep -q "gstreamer"; then
    echo "[OK] GStreamer enabled."
else
    # Check via build info
    GSTREAMER_STATUS=$(grep -i "gstreamer" CMakeCache.txt | head -5)
    echo "[INFO] GStreamer status: $GSTREAMER_STATUS"
fi

# Compile 
echo "[4/6] Compiling OpenCV (this will take 1-2 hours)..."
CORES=$(nproc)
echo "Using $CORES CPU cores..."
make -j$CORES

# Install 
echo "[5/6] Installing OpenCV..."
sudo make install
sudo ldconfig

# Verify 
echo "[6/6] Verifying installation..."
python3 -c "
import cv2
print('OpenCV version:', cv2.__version__)
print('aruco OK:', hasattr(cv2, 'aruco') and hasattr(cv2.aruco, 'ArucoDetector'))

info = cv2.getBuildInformation()
idx = info.find('GStreamer')
if idx != -1:
    snippet = info[idx:idx+30]
    if 'YES' in snippet:
        print('GStreamer: YES')
    else:
        print('GStreamer: NO - CSI camera will not work')
else:
    print('GStreamer: NOT FOUND')
"

echo "================================================"
echo " Build complete!"
echo "================================================"