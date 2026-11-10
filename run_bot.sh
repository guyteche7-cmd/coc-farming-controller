#!/usr/bin/env bash
# =====================================================================
# Clash of Clans Autonomous Farming Controller - Setup & Launcher (macOS)
# Supports BlueStacks on macOS (Intel & Apple Silicon)
# =====================================================================

cd "$(dirname "$0")"

echo "====================================================================="
echo " Clash of Clans Autonomous Farming Controller - macOS Launcher"
echo "====================================================================="
echo ""

# 1. Detect Python 3.10+
PY_CMD=""
if command -v python3 >/dev/null 2>&1; then
    PY_CMD="python3"
elif command -v python >/dev/null 2>&1; then
    PY_CMD="python"
fi

if [ -z "$PY_CMD" ]; then
    echo "[ERROR] Python was not found on your system!"
    echo "Please install Python 3.10+ via Homebrew or from python.org:"
    echo "  brew install python@3.11"
    echo ""
    exit 1
fi

echo "[1/2] Verifying Python environment ($($PY_CMD --version))..."

# 2. Check & auto-install dependencies
if ! $PY_CMD -c "import customtkinter, cv2, mss, rapidocr_onnxruntime, yaml" >/dev/null 2>&1; then
    echo ""
    echo "[*] Installing required dependencies..."
    echo "    Running: $PY_CMD -m pip install -r requirements.txt"
    echo ""
    $PY_CMD -m pip install --upgrade pip >/dev/null 2>&1 || true
    $PY_CMD -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo ""
        echo "[ERROR] Failed to install dependencies!"
        echo "Please verify internet connection and run:"
        echo "  $PY_CMD -m pip install -r requirements.txt"
        echo ""
        exit 1
    fi
    echo "[*] Dependencies installed successfully!"
else
    echo "[*] Core dependencies verified."
fi

# 3. Optimization environment variables for computer vision
export OPENBLAS_NUM_THREADS=1
export OMP_NUM_THREADS=1
export MKL_NUM_THREADS=1
export VECLIB_MAXIMUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

echo ""
echo "[2/2] Launching Clash of Clans Farming Controller..."
echo "---------------------------------------------------------------------"
echo "NOTE FOR MACOS USERS:"
echo "Ensure your Terminal/IDE has Screen Recording & Accessibility enabled"
echo "in macOS: System Settings -> Privacy & Security."
echo "---------------------------------------------------------------------"
echo ""

exec $PY_CMD -m src.app.main "$@"
