import cv2
from src.vision.loot_detector import LootDetector

img_candidate = cv2.imread("assets/test_cases/screen_5_candidate_enemy.png")
detector = LootDetector()
res = detector.detect_candidate_loot(img_candidate)

print(f"Loot Detection Result:")
print(f"Gold: {res.value.gold:,}")
print(f"Elixir: {res.value.elixir:,}")
print(f"Dark Elixir: {res.value.dark_elixir:,}")
print(f"Confidence: {res.confidence:.2f}")
print(f"Valid Candidate: {res.value.is_valid_candidate}")
