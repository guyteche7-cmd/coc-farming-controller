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
        watch_g = getattr(self.config, "watch_gold", False)
        watch_e = getattr(self.config, "watch_elixir", False)
        watch_de = getattr(self.config, "watch_dark_elixir", False)
        watch_comb = getattr(self.config, "watch_combined", False)

        min_g = getattr(self.config, "min_gold", 500000)
        min_e = getattr(self.config, "min_elixir", 500000)
        min_de = getattr(self.config, "min_dark_elixir", 5000)
        min_c = getattr(self.config, "min_combined", 1000000)

        primary_conditions = []
        primary_met = []

        if watch_g:
            primary_conditions.append(f"Gold >= {min_g:,}")
            primary_met.append(gold >= min_g)

        if watch_e:
            primary_conditions.append(f"Elixir >= {min_e:,}")
            primary_met.append(elixir >= min_e)

        if watch_comb:
            primary_conditions.append(f"Combined >= {min_c:,}")
            primary_met.append(combined >= min_c)

        de_condition = None
        de_met = True
        if watch_de:
            de_condition = f"DE >= {min_de:,}"
            de_met = (dark_elixir >= min_de)

        if primary_conditions or de_condition:
            mode = getattr(self.config, "match_mode", "OR").upper()
            de_as_gate = getattr(self.config, "dark_elixir_as_gate", True)

            if mode == "AND":
                all_conds = list(primary_conditions)
                all_met = list(primary_met)
                if de_condition:
                    all_conds.append(de_condition)
                    all_met.append(de_met)
                accepted = all(all_met)
                expr_desc = " AND ".join(all_conds)
            else:  # "OR"
                # If dark_elixir_as_gate is True, Dark Elixir acts as an AND prerequisite
                # rather than allowing 10k DE to accept a base with zero gold/elixir.
                if de_as_gate and de_condition and primary_conditions:
                    primary_accepted = any(primary_met)
                    accepted = primary_accepted and de_met
                    expr_desc = f"({' OR '.join(primary_conditions)}) AND {de_condition}"
                else:
                    all_conds = list(primary_conditions)
                    all_met = list(primary_met)
                    if de_condition:
                        all_conds.append(de_condition)
                        all_met.append(de_met)
                    accepted = any(all_met)
                    expr_desc = " OR ".join(all_conds)

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

