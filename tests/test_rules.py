"""
Unit tests for ExpressionParser, TargetEvaluator, BattleExitEvaluator, WallEvaluator, and ArmyLedger.
"""

import unittest
from src.persistence.config_manager import TargetConfig, DarkElixirConfig, ExitConfig, WallConfig, DeploymentConfig
from src.state.game_state import CandidateInfo, BattleInfo, HomeInfo, BoundingBox
from src.state.army_ledger import ArmyLedger, UnitCategory, UnitStatus
from src.rules.expression_parser import ExpressionEvaluator
from src.rules.target_evaluator import TargetEvaluator
from src.rules.battle_exit_evaluator import BattleExitEvaluator, ExitDecision
from src.rules.wall_evaluator import WallEvaluator


class TestRulesAndState(unittest.TestCase):

    def test_expression_parser_basic(self):
        evaluator = ExpressionEvaluator("gold >= 1000000")
        self.assertTrue(evaluator.evaluate({"gold": 1200000}))
        self.assertFalse(evaluator.evaluate({"gold": 900000}))

    def test_expression_parser_sum(self):
        evaluator = ExpressionEvaluator("gold + elixir >= 1500000")
        self.assertTrue(evaluator.evaluate({"gold": 800000, "elixir": 800000}))
        self.assertFalse(evaluator.evaluate({"gold": 700000, "elixir": 700000}))

    def test_expression_parser_compound_or(self):
        evaluator = ExpressionEvaluator("gold >= 1000000 OR gold + elixir >= 1500000")
        # Case 1: Gold alone >= 1,000,000
        self.assertTrue(evaluator.evaluate({"gold": 1100000, "elixir": 100000}))
        # Case 2: Gold < 1,000,000 but sum >= 1,500,000
        self.assertTrue(evaluator.evaluate({"gold": 800000, "elixir": 750000}))
        # Case 3: Neither
        self.assertFalse(evaluator.evaluate({"gold": 600000, "elixir": 600000}))

    def test_expression_parser_dark_elixir(self):
        evaluator = ExpressionEvaluator("gold + elixir >= 1500000 OR dark_elixir >= 10000")
        self.assertTrue(evaluator.evaluate({"gold": 100000, "elixir": 100000, "dark_elixir": 12000}))
        self.assertFalse(evaluator.evaluate({"gold": 100000, "elixir": 100000, "dark_elixir": 5000}))

    def test_target_evaluator_confidence_gate(self):
        cfg = TargetConfig(expression="gold >= 1000000", min_ocr_confidence=0.75)
        evaluator = TargetEvaluator(cfg)

        # High confidence match
        cand_good = CandidateInfo(gold=1200000, elixir=500000, confidence=0.85)
        res = evaluator.evaluate(cand_good)
        self.assertTrue(res.accepted)

        # Low confidence match -> Must reject!
        cand_low_conf = CandidateInfo(gold=1200000, elixir=500000, confidence=0.60)
        res_low = evaluator.evaluate(cand_low_conf)
        self.assertFalse(res_low.accepted)
        self.assertIn("OCR confidence too low", res_low.reason)

    def test_battle_exit_evaluator(self):
        cfg = ExitConfig(damage_threshold_percent=50.0, surrender_threshold_seconds=60)
        evaluator = BattleExitEvaluator(cfg)

        # 1. Battle progressing, < 50% damage, > 60s
        b1 = BattleInfo(damage_percent=35.0, time_remaining_seconds=120)
        self.assertEqual(evaluator.evaluate(b1).decision, ExitDecision.CONTINUE)

        # 2. Reached 50% damage (e.g. 52%) -> END_BATTLE
        b2 = BattleInfo(damage_percent=52.0, time_remaining_seconds=110)
        self.assertEqual(evaluator.evaluate(b2).decision, ExitDecision.END_BATTLE)

        # 3. Low damage (30%), time reached 60s -> SURRENDER
        b3 = BattleInfo(damage_percent=30.0, time_remaining_seconds=60)
        self.assertEqual(evaluator.evaluate(b3, elapsed_combat_seconds=60.0).decision, ExitDecision.SURRENDER)

        # 4. Priority check: damage >= 50% AND time <= 60s -> END_BATTLE takes precedence
        b4 = BattleInfo(damage_percent=55.0, time_remaining_seconds=45)
        self.assertEqual(evaluator.evaluate(b4).decision, ExitDecision.END_BATTLE)

    def test_wall_evaluator(self):
        cfg = WallConfig(enabled=True, builder_required=True, storage_threshold_percent=80.0)
        evaluator = WallEvaluator(cfg)

        # 1. Storage < 80%, free builders = 1 -> False
        h1 = HomeInfo(gold_storage_fill_percent=60.0, elixir_storage_fill_percent=70.0, free_builders=1, total_builders=5)
        self.assertFalse(evaluator.evaluate(h1).should_upgrade)

        # 2. Gold storage >= 80%, free builders = 1 -> True
        h2 = HomeInfo(gold_storage_fill_percent=85.0, elixir_storage_fill_percent=40.0, free_builders=1, total_builders=5)
        self.assertTrue(evaluator.evaluate(h2).should_upgrade)

        # 3. Gold storage >= 80%, free builders = 0 -> False
        h3 = HomeInfo(gold_storage_fill_percent=90.0, elixir_storage_fill_percent=40.0, free_builders=0, total_builders=5)
        self.assertFalse(evaluator.evaluate(h3).should_upgrade)

    def test_army_ledger_flow(self):
        deploy_cfg = DeploymentConfig()
        ledger = ArmyLedger()
        ledger.initialize_from_config(deploy_cfg)

        # Total slots: valkyrie (40), earthquake (11), log launcher (3), 4 heroes
        self.assertEqual(len(ledger.slots), 7)
        self.assertFalse(ledger.is_fully_deployed)

        # Deploy first troop slot (slot 0)
        valk_slot = ledger.slots[0]
        self.assertEqual(valk_slot.name, deploy_cfg.army.troops[0].name)
        self.assertEqual(valk_slot.remaining_quantity, deploy_cfg.army.troops[0].expected_quantity)

        ledger.record_deployment(0, deploy_cfg.army.troops[0].expected_quantity)
        self.assertEqual(ledger.slots[0].remaining_quantity, 0)
        self.assertEqual(ledger.slots[0].status, UnitStatus.DEPLOYED)

        # Still not fully deployed because heroes/spells remain
        self.assertFalse(ledger.is_fully_deployed)


if __name__ == "__main__":
    unittest.main()
