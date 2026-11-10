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

# 1. Detect Python 3.10+ (Prioritize Homebrew and python.org frameworks ahead of macOS system Python)
CANDIDATES=(
    "/opt/homebrew/bin/python3.12"
    "/opt/homebrew/bin/python3.11"
    "/opt/homebrew/bin/python3.10"
    "/opt/homebrew/bin/python3"
    "/usr/local/bin/python3.12"
    "/usr/local/bin/python3.11"
    "/usr/local/bin/python3.10"
    "/usr/local/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3"
    "/Library/Frameworks/Python.framework/Versions/3.10/bin/python3"
    "python3"
    "python"
)

PY_CMD=""
for cand in "${CANDIDATES[@]}"; do
    if command -v "$cand" >/dev/null 2>&1; then
        if "$cand" -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" >/dev/null 2>&1; then
            PY_CMD="$cand"
            break
        fi
    fi
done

if [ -z "$PY_CMD" ]; then
    echo "[ERROR] Python 3.10+ was not found on your system!"
    echo "macOS system Python (/usr/bin/python3) is outdated and has known Tcl/Tk GUI display bugs."
    echo "Please install modern Python 3.11+ via Homebrew or from python.org:"
    echo "  brew install python@3.11"
    echo "Or download the official installer from: https://www.python.org/downloads/macos/"
    echo ""
    exit 1
fi

# Silence legacy macOS Tkinter deprecation popup
export TK_SILENCE_DEPRECATION=1

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
