"""
Unit tests for Deployment Planner and Wall Planner.
"""

import unittest
from src.state.army_ledger import ArmyLedger
from src.planning.deployment_planner import DeploymentPlanner, ActionType
from src.planning.wall_planner import WallPlanner


class TestDeploymentPlanner(unittest.TestCase):

    def test_deployment_plan_generation(self):
        ledger = ArmyLedger()
        ledger.initialize_baseline()

        planner = DeploymentPlanner(edge="top")
        plan = planner.generate_plan(ledger)

        self.assertGreater(len(plan), 0)

        # First action should be selecting regular troops (Slot 0)
        self.assertEqual(plan[0].action_type, ActionType.SELECT_SLOT)
        self.assertEqual(plan[0].target_name, "Troops (Slot 0)")

        # Check that heroes and sieges are included
        target_names = [a.target_name for a in plan]
        self.assertIn("Siege Machine (Slot 1)", target_names)
        self.assertIn("Cast Spells", target_names)
        self.assertTrue(any("Hero" in name for name in target_names))

    def test_edge_coordinates(self):
        planner = DeploymentPlanner(edge="top")
        points = planner.get_probe_points()
        self.assertGreater(len(points), 0)
        for px, py in points:
            self.assertTrue(0.0 <= px <= 1.0)
            self.assertTrue(0.0 <= py <= 1.0)

    def test_wall_planner(self):
        planner = WallPlanner(batch_enabled=True)
        plan = planner.generate_upgrade_plan(0)
        self.assertEqual(len(plan), 3)
        self.assertEqual(plan[0].target_name, "wall_segment")
        self.assertEqual(plan[1].target_name, "batch_wall_select")
        self.assertEqual(plan[2].target_name, "upgrade_confirm")


if __name__ == "__main__":
    unittest.main()
