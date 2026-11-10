"""
Target Candidate Evaluator.
Evaluates candidate village loot against user-defined expression rules and Dark Elixir settings.
"""

from __future__ import annotations
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.state.game_state import CandidateInfo
from src.rules.expression_parser import ExpressionEvaluator


class TargetEvaluationResult(BaseModel):
    accepted: bool
    reason: str
    expression: str
    values: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = 0.0


class TargetEvaluator:
    """Evaluates whether a candidate village should be attacked or skipped."""

    def __init__(self, target_config):
        self.config = target_config
        self.evaluator = ExpressionEvaluator(target_config.expression)

    def update_expression(self, expression_str: str) -> None:
        """Updates the expression dynamically."""
        self.evaluator = ExpressionEvaluator(expression_str)
        self.config.expression = expression_str

    def evaluate(self, candidate: CandidateInfo) -> TargetEvaluationResult:
        """Evaluates candidate village against rules."""
        # Sanity & confidence check
        if candidate.confidence < self.config.min_ocr_confidence:
            return TargetEvaluationResult(
                accepted=False,
                reason=f"OCR confidence too low ({candidate.confidence:.2f} < {self.config.min_ocr_confidence:.2f})",
                expression=self.config.expression,
                values={"gold": candidate.gold, "elixir": candidate.elixir, "dark_elixir": candidate.dark_elixir},
                confidence=candidate.confidence
            )

        gold = candidate.gold
        elixir = candidate.elixir
        dark_elixir = candidate.dark_elixir
        combined = gold + elixir

        context = {
            "gold": gold,
            "elixir": elixir,
            "dark_elixir": dark_elixir,
            "combined": combined
        }

        # Check explicit Dark Elixir gate if enabled in config
        if hasattr(self.config, "dark_elixir") and self.config.dark_elixir.enabled:
            if candidate.dark_elixir < self.config.dark_elixir.minimum:
                return TargetEvaluationResult(
                    accepted=False,
                    reason=f"Dark Elixir below minimum ({candidate.dark_elixir:,} < {self.config.dark_elixir.minimum:,})",
                    expression=getattr(self.config, "expression", ""),
                    values=context,
                    confidence=candidate.confidence
                )

        # 1. Evaluate user-selected watch parameters (Checkboxes)
        active_conditions = []
        conditions_met = []

        if getattr(self.config, "watch_gold", False):
            min_g = getattr(self.config, "min_gold", 500000)
            active_conditions.append(f"Gold >= {min_g:,}")
            conditions_met.append(gold >= min_g)

        if getattr(self.config, "watch_elixir", False):
            min_e = getattr(self.config, "min_elixir", 500000)
            active_conditions.append(f"Elixir >= {min_e:,}")
            conditions_met.append(elixir >= min_e)

        if getattr(self.config, "watch_dark_elixir", False):
            min_de = getattr(self.config, "min_dark_elixir", 5000)
            active_conditions.append(f"DE >= {min_de:,}")
            conditions_met.append(dark_elixir >= min_de)

        if getattr(self.config, "watch_combined", False):
            min_c = getattr(self.config, "min_combined", 1000000)
            active_conditions.append(f"Combined >= {min_c:,}")
            conditions_met.append(combined >= min_c)

        if active_conditions:
            mode = getattr(self.config, "match_mode", "OR").upper()
            if mode == "AND":
                accepted = all(conditions_met)
            else:  # "OR"
                accepted = any(conditions_met)

            expr_desc = f" {mode} ".join(active_conditions)
            reason = f"Loot accepted ({expr_desc})" if accepted else f"Loot below target ({expr_desc})"
            return TargetEvaluationResult(
                accepted=accepted,
                reason=reason,
                expression=expr_desc,
                values=context,
                confidence=candidate.confidence
            )

        # 2. Fallback to freeform expression evaluation
        try:
            matched = self.evaluator.evaluate(context)
            if matched:
                return TargetEvaluationResult(
                    accepted=True,
                    reason="Target met expression requirements",
                    expression=self.config.expression,
                    values=context,
                    confidence=candidate.confidence
                )
            else:
                return TargetEvaluationResult(
                    accepted=False,
                    reason="Loot below configured thresholds",
                    expression=self.config.expression,
                    values=context,
                    confidence=candidate.confidence
                )
        except Exception as e:
            return TargetEvaluationResult(
                accepted=False,
                reason=f"Evaluation error: {str(e)}",
                expression=self.config.expression,
                values=context,
                confidence=candidate.confidence
            )

