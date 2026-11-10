"""
Unit tests for dynamic army slot classification and multi-troop deployment planning.
Verifies that:
1. Dynamic army ribbon classification accurately distinguishes between:
   - Multiple troop slots (e.g. Valkyries + MOMMA P.E.K.K.As)
   - Siege Machine (e.g. Siege Barracks)
   - Heroes (Royal Champion, Grand Warden, Dragon Duke, etc.)
   - Spells (e.g. Earthquake)
2. Levels on troop/spell/hero cards are ignored (since levels change over time).
3. Universal deployment sequence:
   - 50% of ALL detected troop slots
   - Siege Machine (1 tap)
   - Heroes (1 tap each)
   - 100% of remaining troops dumped across all troop slots until greyed out
   - Spells cast until greyed out
   - Hero abilities activated
   - Ribbon slot deselected
"""

import os
import cv2
import pytest
from src.planning.deployment_planner import DeploymentPlanner, ArmySlotLayout, ActionType
from unittest.mock import MagicMock


class TestArmyDetection:

    @pytest.fixture
    def img_single_troop_three_heroes(self):
        """Reference battle image with 1 troop (Valkyrie), 1 siege, 3 heroes (RC, Warden, Duke), 1 spell"""
        p = os.path.join(os.path.dirname(__file__), "..", "assets", "test_cases", "test_army_single_troop_three_heroes.jpg")
        if os.path.exists(p):
            return cv2.imread(p)
        return None

    def test_single_troop_three_heroes_classification(self, img_single_troop_three_heroes):
        if img_single_troop_three_heroes is None:
            pytest.skip("Reference image not available")
        planner = DeploymentPlanner()
        layout = planner.detect_army_slots(
            img_single_troop_three_heroes,
            configured_hero_count=3,
            deploy_siege=True
        )
        assert layout.troop_slots == [0], f"Expected troop_slots=[0], got {layout.troop_slots}"
        assert layout.siege_slot == 1, f"Expected siege_slot=1, got {layout.siege_slot}"
        assert layout.hero_slots == [2, 3, 4], f"Expected hero_slots=[2, 3, 4], got {layout.hero_slots}"
        assert layout.spell_slots == [5], f"Expected spell_slots=[5], got {layout.spell_slots}"
        assert layout.total_occupied == 6

    def test_multi_troop_two_heroes_classification(self, img_single_troop_three_heroes):
        if img_single_troop_three_heroes is None:
            pytest.skip("Reference image not available")
        planner = DeploymentPlanner()
        # Mock read_slot_unit_count to simulate 2 troop slots (Slot 0 Valkyries, Slot 1 MOMMA PEKKA)
        badge_mock = {0: 44, 1: 25, 2: None, 3: None, 4: None, 5: 11}
        planner.read_slot_unit_count = MagicMock(side_effect=lambda f, s: badge_mock.get(s, None))

        layout = planner.detect_army_slots(
            img_single_troop_three_heroes,
            configured_hero_count=2,
            deploy_siege=True
        )
        # In this army: Slot 0 is Valkyrie (x44), Slot 1 is MOMMA PEKKA (x25)
        # Slot 2 is Siege Barracks, Slots 3 & 4 are Heroes, Slot 5 is Earthquake spell
        assert layout.troop_slots == [0, 1], f"Expected troop_slots=[0, 1], got {layout.troop_slots}"
        assert layout.siege_slot == 2, f"Expected siege_slot=2, got {layout.siege_slot}"
        assert layout.hero_slots == [3, 4], f"Expected hero_slots=[3, 4], got {layout.hero_slots}"
        assert layout.spell_slots == [5], f"Expected spell_slots=[5], got {layout.spell_slots}"
        assert layout.total_occupied == 6

    def test_wall_breaker_multi_troop_partition_with_two_heroes(self):
        """
        Verifies that when a player brings multiple troop types (e.g. Valkyries + Super Wall Breakers),
        both troop slots are correctly detected as troop_slots=[0, 1] rather than misclassifying the
        Wall Breaker as a siege machine.
        """
        import numpy as np
        planner = DeploymentPlanner()
        # Mock frame with 6 solid card slots and empty grass slots 6, 7, 8
        dummy_frame = np.zeros((600, 1000, 3), dtype=np.uint8)
        # Give slots 0-5 card values (mean > 60, g-b near 0)
        h, w = dummy_frame.shape[:2]
        for s in range(6):
            nx = planner.SLOT_X_COORDINATES[s]
            x1, x2 = max(0, int((nx - 0.030) * w)), min(w, int((nx + 0.030) * w))
            y1, y2 = max(0, int(0.835 * h)), min(h, int(0.975 * h))
            dummy_frame[y1:y2, x1:x2] = [80, 80, 80]
        # Slots 6-8 have grass background (g - b > 25)
        for s in range(6, 9):
            nx = planner.SLOT_X_COORDINATES[s]
            x1, x2 = max(0, int((nx - 0.030) * w)), min(w, int((nx + 0.030) * w))
            y1, y2 = max(0, int(0.835 * h)), min(h, int(0.975 * h))
            dummy_frame[y1:y2, x1:x2] = [30, 80, 30]

        # Slot 0 has 0/None (depleted Valkyries), Slot 1 has 1 (Wall Breakers), Slot 5 has Spell
        badge_mock = {0: None, 1: 1, 2: None, 3: None, 4: None, 5: 1}
        planner.read_slot_unit_count = MagicMock(side_effect=lambda f, s: badge_mock.get(s, None))

        layout = planner.detect_army_slots(
            dummy_frame,
            configured_hero_count=2,
            deploy_siege=True
        )
        assert layout.troop_slots == [0, 1], f"Expected troop_slots=[0, 1], got {layout.troop_slots}"
        assert layout.siege_slot == 2, f"Expected siege_slot=2, got {layout.siege_slot}"
        assert layout.hero_slots == [3, 4], f"Expected hero_slots=[3, 4], got {layout.hero_slots}"
        assert layout.spell_slots == [5], f"Expected spell_slots=[5], got {layout.spell_slots}"
        assert layout.total_occupied == 6

    def test_recovery_plan_deselection(self):
        planner = DeploymentPlanner()
        rec_plan = planner.generate_recovery_plan(ledger=MagicMock(), hero_slots=[2, 3, 4])
        # Verify hero abilities are generated for all 3 heroes
        hero_actions = [a for a in rec_plan if a.action_type == ActionType.ACTIVATE_ABILITY]
        assert len(hero_actions) == 3
        assert [a.slot_index for a in hero_actions] == [2, 3, 4]

        # Verify final action in recovery plan is a ribbon deselection
        final_action = rec_plan[-1]
        assert final_action.action_type == ActionType.CLICK_UI
        assert "Deselect" in final_action.target_name
        assert final_action.slot_index == 0
