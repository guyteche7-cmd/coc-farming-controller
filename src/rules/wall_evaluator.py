"""
Wall Upgrade Trigger and Loop Evaluator.
Evaluates storage fullness and builder requirements to determine when to upgrade walls.
"""

from __future__ import annotations
from pydantic import BaseModel
from src.state.game_state import HomeInfo


class WallEvaluationResult(BaseModel):
    should_upgrade: bool
    reason: str
    gold_fill_percent: float
    elixir_fill_percent: float
    free_builders: int


class WallEvaluator:
    """Evaluates whether wall upgrades should be triggered upon returning Home."""

    def __init__(self, wall_config):
        self.config = wall_config

    def evaluate(self, home_info: HomeInfo) -> WallEvaluationResult:
        if not self.config.enabled:
            return WallEvaluationResult(
                should_upgrade=False,
                reason="Wall upgrade mode is disabled in configuration",
                gold_fill_percent=home_info.gold_storage_fill_percent,
                elixir_fill_percent=home_info.elixir_storage_fill_percent,
                free_builders=home_info.free_builders
            )

        # Check builder requirement if configured
        if self.config.builder_required and home_info.free_builders < 1:
            return WallEvaluationResult(
                should_upgrade=False,
                reason=f"No free builders available ({home_info.free_builders}/{home_info.total_builders})",
                gold_fill_percent=home_info.gold_storage_fill_percent,
                elixir_fill_percent=home_info.elixir_storage_fill_percent,
                free_builders=home_info.free_builders
            )

        # Check storage fill thresholds (Gold >= 80% OR Elixir >= 80%)
        thresh = self.config.storage_threshold_percent
        gold_ok = home_info.gold_storage_fill_percent >= thresh
        elixir_ok = home_info.elixir_storage_fill_percent >= thresh

        if gold_ok or elixir_ok:
            resource_met = "Gold" if (gold_ok and not elixir_ok) else ("Elixir" if (elixir_ok and not gold_ok) else "Both Gold & Elixir")
            return WallEvaluationResult(
                should_upgrade=True,
                reason=f"{resource_met} storage fill reached threshold ({max(home_info.gold_storage_fill_percent, home_info.elixir_storage_fill_percent):.1f}% >= {thresh:.1f}%)",
                gold_fill_percent=home_info.gold_storage_fill_percent,
                elixir_fill_percent=home_info.elixir_storage_fill_percent,
                free_builders=home_info.free_builders
            )

        return WallEvaluationResult(
            should_upgrade=False,
            reason=f"Storage below upgrade threshold ({home_info.gold_storage_fill_percent:.1f}% Gold, {home_info.elixir_storage_fill_percent:.1f}% Elixir < {thresh:.1f}%)",
            gold_fill_percent=home_info.gold_storage_fill_percent,
            elixir_fill_percent=home_info.elixir_storage_fill_percent,
            free_builders=home_info.free_builders
        )
