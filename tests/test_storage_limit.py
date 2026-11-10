import os
import cv2
import pytest
from src.persistence.database import DatabaseManager
from src.persistence.config_manager import RuntimeConfig
from src.vision.storage_inspector import StorageInspector

MEDIA_DIR = r"C:\Users\ayush\.gemini\antigravity\brain\ee06cf55-ba4c-4e33-9044-86a7acf46bc2\.user_uploaded"

def test_database_player_limits(tmp_path):
    test_db_path = str(tmp_path / "test_farming.db")
    db = DatabaseManager(test_db_path)
    
    # Initially None
    assert db.get_player_storage_limits("AyushSTK") is None
    
    # Save limits
    db.save_player_storage_limits("AyushSTK", 31000000, 31000000, 350000)
    
    # Retrieve limits
    limits = db.get_player_storage_limits("AyushSTK")
    assert limits is not None
    assert limits["max_gold"] == 31000000
    assert limits["max_elixir"] == 31000000
    assert limits["max_dark_elixir"] == 350000

def test_storage_inspector_player_id():
    inspector = StorageInspector()
    img_path = os.path.join(MEDIA_DIR, "media_1793714263059_32d1300e.jpg")
    img = cv2.imread(img_path)
    assert img is not None
    
    player_name = inspector.detect_player_name(img)
    print("Detected player name:", player_name)
    assert "ayush" in player_name.lower() or "stk" in player_name.lower()

def test_storage_inspector_tooltips():
    inspector = StorageInspector()
    
    # Gold tooltip
    gold_img_path = os.path.join(MEDIA_DIR, "media_1793714263080_377b142f.jpg")
    gold_img = cv2.imread(gold_img_path)
    assert gold_img is not None
    max_gold = inspector.read_max_capacity_tooltip(gold_img, resource_type="gold")
    print("Detected Max Gold:", max_gold)
    assert max_gold == 31000000
    
    # Elixir tooltip
    elixir_img_path = os.path.join(MEDIA_DIR, "media_1793714263098_16067084.jpg")
    elixir_img = cv2.imread(elixir_img_path)
    assert elixir_img is not None
    max_elixir = inspector.read_max_capacity_tooltip(elixir_img, resource_type="elixir")
    print("Detected Max Elixir:", max_elixir)
    assert max_elixir == 31000000

if __name__ == "__main__":
    import tempfile
    from pathlib import Path
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as td:
        test_database_player_limits(Path(td))
    test_storage_inspector_player_id()
    test_storage_inspector_tooltips()
    print("ALL TESTS PASSED SUCCESSFULLY!")
