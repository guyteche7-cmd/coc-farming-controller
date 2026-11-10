import sys
import os

sys.path.insert(0, os.path.abspath("."))

from src.utils.audit_logger import audit_logger

audit_logger.log_detection("HOME", 0.98, "Attack button detected on Home screen")
audit_logger.log_action("HOME_ATTACK_BUTTON", 108, 952, 0.056, 0.885, "Opening attack menu")
audit_logger.log_detection("ATTACK_MENU", 0.95, "Multiplayer card detected")
audit_logger.log_action("FIND_A_MATCH_BATTLE_BUTTON", 342, 765, 0.178, 0.710, "Selecting Multiplayer Battle")
audit_logger.log_loot_scan(1, 846531, 854692, 7563, 0.94, True, "Exceeds minimum threshold")
audit_logger.log_deployment_step(0, "Valkyries", 620, 41, 0.605, 0.071, 12, "Dropping army wave at marked spot")
audit_logger.log_hero_ability(2, "Minion Prince", 271, 921, 0.265, 0.900)
audit_logger.log_combat_status(52.0, 1, 0.0, "Target damage reached")
audit_logger.log_battle_exit("VICTORY", 52.0, 1, "RETURN_HOME_BUTTON", 507, 885)

print(f"Sample audit log written to: {audit_logger.file_path}")
