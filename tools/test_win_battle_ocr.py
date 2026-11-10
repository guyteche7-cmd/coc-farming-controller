import cv2
from src.vision.battle_detector import BattleDetector

img_win = cv2.imread("assets/test_cases/screen_10_active_battle_win.png")
detector = BattleDetector()
res = detector.detect_battle_status(img_win)

print(f"Battle Status Result (Win Screen):")
print(f"Damage %: {res.value.damage_percent}")
print(f"Time remaining: {res.value.time_remaining_seconds}s")
print(f"Stars: {res.value.stars}")
print(f"Can end battle: {res.value.can_end_battle}")
print(f"Can surrender: {res.value.can_surrender}")
print(f"Confidence: {res.confidence:.2f}")
