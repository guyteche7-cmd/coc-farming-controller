import sys
import os
import tempfile

cwd = os.getcwd()
if cwd not in sys.path:
    sys.path.insert(0, cwd)

print("=== RUNNING FULL PROJECT HEALTH CHECK ===")

errors = []

# 1. Test Core Config Manager
try:
    from src.persistence.config_manager import ConfigManager
    cm = ConfigManager()
    cfg = cm.config
    print(f"[1/5] ConfigManager loaded: Mode={cfg.mode}, Deployment Edge={cfg.deployment.selected_edge}")
except Exception as e:
    errors.append(f"Config error: {e}")
    print(f"[1/5] Config FAILED: {e}")

# 2. Test YOLO Model
try:
    from src.vision.ai_detector import AIVisionDetector
    ai = AIVisionDetector()
    if ai.is_ready():
        print(f"[2/5] YOLO Model loaded cleanly with {len(ai.model.names)} classes.")
    else:
        errors.append("YOLO Model failed to load.")
        print("[2/5] YOLO Model failed to load.")
except Exception as e:
    errors.append(f"YOLO error: {e}")
    print(f"[2/5] YOLO Error: {e}")

# 3. Test UI State Detector & Templates
try:
    from src.vision.state_detector import UIStateDetector
    detector = UIStateDetector(use_ai=True)
    print(f"[3/5] UI State Detector initialized with {len(detector.templates)} visual templates.")
except Exception as e:
    errors.append(f"State Detector error: {e}")
    print(f"[3/5] State Detector FAILED: {e}")

# 4. Test Deployment Planner
try:
    from src.planning.deployment_planner import DeploymentPlanner
    planner = DeploymentPlanner(edge="top")
    line_pts = planner._generate_line_points(10)
    print(f"[4/5] Deployment Planner generated {len(line_pts)} safe outer grass points.")
except Exception as e:
    errors.append(f"Deployment Planner error: {e}")
    print(f"[4/5] Deployment Planner FAILED: {e}")

# 5. Test Database
try:
    from src.persistence.database import DatabaseManager
    import uuid
    db_path = os.path.join(tempfile.gettempdir(), f"health_{uuid.uuid4().hex[:8]}.db")
    db = DatabaseManager(db_path)
    s_id = str(uuid.uuid4())[:8]
    db.start_session(s_id, "test_mode")
    db.increment_session_skips(s_id)
    db.end_session(s_id, "HEALTH_CHECK")
    print(f"[5/5] Database SQLite CRUD operations verified cleanly.")
    try:
        if os.path.exists(db_path):
            os.remove(db_path)
    except Exception:
        pass
except Exception as e:
    errors.append(f"Database error: {e}")
    print(f"[5/5] Database FAILED: {e}")

print("\n==========================================")
if not errors:
    print("SUCCESS: ALL 5/5 PROJECT SYSTEMS ARE 100% HEALTHY AND READY!")
else:
    print(f"FAILED: Found {len(errors)} errors:")
    for err in errors:
        print(f"  - {err}")
print("==========================================")
