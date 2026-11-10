import subprocess
import sys

cmd = [sys.executable, "-c", "import easyocr; r = easyocr.Reader(['en'], gpu=False)"]
res = subprocess.run(cmd, capture_output=True, text=True)
print("Return code:", res.returncode)
print("Stdout:", res.stdout)
print("Stderr:", res.stderr)
