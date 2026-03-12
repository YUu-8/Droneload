#!/bin/bash
# test_camera.sh - Test CSI camera GStreamer pipeline on RubikPi3

echo "========================================"
echo " CSI Camera Pipeline Test"
echo "========================================"

# Check if qtiqmmfsrc is available
echo "[1/2] Checking qtiqmmfsrc plugin..."
if gst-inspect-1.0 qtiqmmfsrc > /dev/null 2>&1; then
    echo "      OK - qtiqmmfsrc found"
else
    echo "      FAIL - qtiqmmfsrc not found"
    echo "      -> Run ./setup.sh first"
    exit 1
fi

#  Test pipeline
echo "[2/2] Testing camera pipeline (Ctrl+C to stop)..."
echo ""

gst-launch-1.0 qtiqmmfsrc camera=0 ! \
    "video/x-raw(memory:GBM),format=NV12,width=1280,height=720,framerate=30/1" ! \
    qtivtransform ! \
    "video/x-raw,format=BGRx" ! \
    videoconvert ! \
    "video/x-raw,format=BGR" ! \
    fakesink

# Check exit code
if [ $? -eq 0 ] || [ $? -eq 130 ]; then
    # 130 = Ctrl+C, which is normal
    echo ""
    echo "Pipeline OK - camera is working"
    echo "You can now run: python3 main.py"
else
    echo ""
    echo "Pipeline FAILED - check error above"
    echo "Common fixes:"
    echo "  - Check camera cable connection"
    echo "  - Try different resolution: change 1280x720 to 1920x1080"
    echo "  - Run: gst-inspect-1.0 qtiqmmfsrc  (to see supported formats)"
fi