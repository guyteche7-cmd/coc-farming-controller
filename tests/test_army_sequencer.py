"""
Unit tests for Army Slot Layout Partitioning and Drop Sequencer.
Verifies that:
- Troops, Siege, Heroes, and Spells are deterministically partitioned.
- Siege machines are NEVER misclassified as heroes or spammed as troops.
- Spells are NEVER skipped.
- Hero abilities are activated ONLY on actual hero slots.
"""

import unittest
from src.persistence.config_manager import (
    ArmyConfig, TroopUnitConfig, SiegeUnitConfig, HeroUnitConfig, SpellUnitConfig
)
from src.planning.deployment_planner import DeploymentPlanner, ActionType


class TestArmySequencer(unittest.TestCase):

    def setUp(self):
        self.planner = DeploymentPlanner(edge="top")

    def test_eight_slot_layout_partition(self):
        """
        User Army: 2 troops (Valkyrie, Wall Breaker) + 1 Siege (Siege Barracks) +
        4 Heroes (Minion Prince, Queen, Warden, King) + 1 Spell (Earthquake) = 8 slots.
        Matches screenshot media_1794330231297_bf9eeebd.jpg.
        """
        army = ArmyConfig(
            troops=[
                TroopUnitConfig(name="valkyrie", expected_quantity=24, priority=1, enabled=True),
                TroopUnitConfig(name="super_wall_breaker", expected_quantity=4, priority=2, enabled=True),
            ],
            siege=[
                SiegeUnitConfig(name="siege_barracks", expected_quantity=1, enabled=True)
            ],
            heroes=[
                HeroUnitConfig(name="minion_prince", enabled=True),
                HeroUnitConfig(name="archer_queen", enabled=True),
                HeroUnitConfig(name="grand_warden", enabled=True),
                HeroUnitConfig(name="barbarian_king", enabled=True),
            ],
            spells=[
                SpellUnitConfig(name="earthquake", expected_quantity=11, enabled=True)
            ]
        )

        layout = self.planner.detect_army_slots(
            frame_bgr=None,
            configured_hero_count=4,
            deploy_siege=True,
            configured_army=army
        )

        # Invariant Assertions
        self.assertEqual(layout.troop_slots, [0, 1], "Slots 0 and 1 must be troops")
        self.assertEqual(layout.siege_slot, 2, "Slot 2 must be the Siege Machine")
        self.assertEqual(layout.hero_slots, [3, 4, 5, 6], "Slots 3, 4, 5, 6 must be the 4 Heroes")
        self.assertEqual(layout.spell_slots, [7], "Slot 7 must be Earthquake Spells")

        # Plan generation assertions
        plan = self.planner.generate_full_deployment_plan(
            confirmed_x=0.6055,
            confirmed_y=0.0712,
            layout=layout
        )

        # 1. Verify Siege Machine is deployed with exactly 1 tap at Slot 2
        siege_deploys = [
            a for a in plan
            if a.action_type == ActionType.DEPLOY_POINT and a.slot_index == 2
        ]
        self.assertEqual(len(siege_deploys), 1, "Siege machine must be deployed with 1 tap")
        self.assertEqual(siege_deploys[0].tap_count, 1, "Siege machine must NOT be multi-tapped")

        # 2. Verify Spell deployment on Slot 7
        spell_deploys = [
            a for a in plan
            if a.slot_index == 7 and a.action_type == ActionType.DEPLOY_POINT
        ]
        self.assertGreater(len(spell_deploys), 0, "Spells on Slot 7 must be deployed")

        # 3. Verify Hero abilities are triggered ONLY on slots 3, 4, 5, 6
        ability_actions = [
            a for a in plan
            if a.action_type == ActionType.ACTIVATE_ABILITY
        ]
        ability_slots = [a.slot_index for a in ability_actions]
        self.assertEqual(ability_slots, [3, 4, 5, 6], "Hero abilities must ONLY target hero slots")
        self.assertNotIn(2, ability_slots, "Siege Machine (Slot 2) must NEVER be clicked for hero ability")
        self.assertNotIn(7, ability_slots, "Spells (Slot 7) must NEVER be clicked for hero ability")

    def test_seven_slot_layout_partition(self):
        """
        User Army: 1 troop (Sneaky Goblin) + 1 Siege + 4 Heroes + 1 Spell = 7 slots.
        """
        army = ArmyConfig(
            troops=[TroopUnitConfig(name="sneaky_goblin", expected_quantity=90, enabled=True)],
            siege=[SiegeUnitConfig(name="battle_blimp", expected_quantity=1, enabled=True)],
            heroes=[
                HeroUnitConfig(name="minion_prince", enabled=True),
                HeroUnitConfig(name="archer_queen", enabled=True),
                HeroUnitConfig(name="grand_warden", enabled=True),
                HeroUnitConfig(name="barbarian_king", enabled=True),
            ],
            spells=[SpellUnitConfig(name="jump", expected_quantity=4, enabled=True)]
        )

        layout = self.planner.detect_army_slots(
            frame_bgr=None,
            configured_hero_count=4,
            deploy_siege=True,
            configured_army=army
        )

        self.assertEqual(layout.troop_slots, [0])
        self.assertEqual(layout.siege_slot, 1)
        self.assertEqual(layout.hero_slots, [2, 3, 4, 5])
        self.assertEqual(layout.spell_slots, [6])

    def test_zero_siege_layout_partition(self):
        """
        User Army without Siege Machine: 2 troops + 4 Heroes + 1 Spell = 7 slots.
        """
        army = ArmyConfig(
            troops=[
                TroopUnitConfig(name="dragon", expected_quantity=12, enabled=True),
                TroopUnitConfig(name="balloon", expected_quantity=10, enabled=True),
            ],
            siege=[SiegeUnitConfig(name="none", expected_quantity=0, enabled=False)],
            heroes=[
                HeroUnitConfig(name="archer_queen", enabled=True),
                HeroUnitConfig(name="grand_warden", enabled=True),
                HeroUnitConfig(name="barbarian_king", enabled=True),
                HeroUnitConfig(name="royal_champion", enabled=True),
            ],
            spells=[SpellUnitConfig(name="rage", expected_quantity=5, enabled=True)]
        )

        layout = self.planner.detect_army_slots(
            frame_bgr=None,
            configured_hero_count=4,
            deploy_siege=False,
            configured_army=army
        )

        self.assertEqual(layout.troop_slots, [0, 1])
        self.assertIsNone(layout.siege_slot)
        self.assertEqual(layout.hero_slots, [2, 3, 4, 5])
        self.assertEqual(layout.spell_slots, [6])


if __name__ == "__main__":
    unittest.main()
