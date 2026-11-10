import cv2
from src.vision.battle_detector import BattleDetector

img_battle = cv2.imread("assets/test_cases/screen_7_active_battle.png")
detector = BattleDetector()
res = detector.detect_battle_status(img_battle)

print(f"Battle Status Result:")
print(f"Damage %: {res.value.damage_percent}")
print(f"Time remaining: {res.value.time_remaining_seconds}s")
print(f"Can surrender: {res.value.can_surrender}")
print(f"Can end battle: {res.value.can_end_battle}")
print(f"Confidence: {res.confidence:.2f}")
