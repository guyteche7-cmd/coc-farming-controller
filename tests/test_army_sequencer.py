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

    def test_six_heroes_th17_layout_partition(self):
        """
        Town Hall 17 Full Roster Army:
        2 troops (Valkyrie, Super Wall Breaker) +
        1 Siege Machine (Siege Barracks) +
        6 Heroes (Barbarian King, Archer Queen, Grand Warden, Royal Champion, Minion Prince, Dragon Duke) +
        2 Spells (Earthquake x8, Freeze x3)
        Total = 11 slots!
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
                HeroUnitConfig(name="barbarian_king", enabled=True),
                HeroUnitConfig(name="archer_queen", enabled=True),
                HeroUnitConfig(name="grand_warden", enabled=True),
                HeroUnitConfig(name="royal_champion", enabled=True),
                HeroUnitConfig(name="minion_prince", enabled=True),
                HeroUnitConfig(name="dragon_duke", enabled=True),
            ],
            spells=[
                SpellUnitConfig(name="earthquake", expected_quantity=8, enabled=True),
                SpellUnitConfig(name="freeze", expected_quantity=3, enabled=True),
            ]
        )

        layout = self.planner.detect_army_slots(
            frame_bgr=None,
            configured_hero_count=6,
            deploy_siege=True,
            configured_army=army
        )

        # Invariant Assertions:
        self.assertEqual(layout.troop_slots, [0, 1], "Slots 0, 1 must be troops")
        self.assertEqual(layout.siege_slot, 2, "Slot 2 must be the Siege Machine")
        self.assertEqual(layout.hero_slots, [3, 4, 5, 6, 7, 8], "Slots 3-8 must be all 6 Heroes")
        self.assertEqual(layout.spell_slots, [9, 10], "Slots 9, 10 must be the 2 Spells")

        # Plan generation assertions:
        plan = self.planner.generate_full_deployment_plan(
            confirmed_x=0.6055,
            confirmed_y=0.0712,
            layout=layout
        )

        # 1. Verify all 6 heroes are deployed
        hero_deploys = [
            a for a in plan
            if a.action_type == ActionType.DEPLOY_POINT and a.slot_index in [3, 4, 5, 6, 7, 8]
        ]
        self.assertEqual(len(hero_deploys), 6, "All 6 heroes must have deployment actions")

        # 2. Verify all 6 hero abilities are triggered
        ability_actions = [
            a for a in plan
            if a.action_type == ActionType.ACTIVATE_ABILITY
        ]
        ability_slots = [a.slot_index for a in ability_actions]
        self.assertEqual(ability_slots, [3, 4, 5, 6, 7, 8], "Hero abilities must trigger on all 6 hero slots")

        # 3. Verify both spell slots (9 and 10) are cast
        spell_deploys = [
            a for a in plan
            if a.action_type == ActionType.DEPLOY_POINT and a.slot_index in [9, 10]
        ]
        self.assertEqual(len(spell_deploys), 2, "Both spell slots (9 and 10) must be cast")

    def test_dynamic_five_troop_slots(self):
        """
        Dynamic troops: 5 different troops + 1 siege + 4 heroes + 1 spell = 11 slots.
        """
        army = ArmyConfig(
            troops=[
                TroopUnitConfig(name="valkyrie", expected_quantity=10, priority=1, enabled=True),
                TroopUnitConfig(name="super_wall_breaker", expected_quantity=4, priority=2, enabled=True),
                TroopUnitConfig(name="healer", expected_quantity=4, priority=3, enabled=True),
                TroopUnitConfig(name="wizard", expected_quantity=6, priority=4, enabled=True),
                TroopUnitConfig(name="archer", expected_quantity=10, priority=5, enabled=True),
            ],
            siege=[SiegeUnitConfig(name="flame_flinger", expected_quantity=1, enabled=True)],
            heroes=[
                HeroUnitConfig(name="archer_queen", enabled=True),
                HeroUnitConfig(name="grand_warden", enabled=True),
                HeroUnitConfig(name="barbarian_king", enabled=True),
                HeroUnitConfig(name="royal_champion", enabled=True),
            ],
            spells=[SpellUnitConfig(name="rage", expected_quantity=3, enabled=True)]
        )

        layout = self.planner.detect_army_slots(
            frame_bgr=None,
            configured_hero_count=4,
            deploy_siege=True,
            configured_army=army
        )

        self.assertEqual(layout.troop_slots, [0, 1, 2, 3, 4])
        self.assertEqual(layout.siege_slot, 5)
        self.assertEqual(layout.hero_slots, [6, 7, 8, 9])
        self.assertEqual(layout.spell_slots, [10])


if __name__ == "__main__":
    unittest.main()
