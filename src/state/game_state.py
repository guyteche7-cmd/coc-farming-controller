"""
Runtime Game State Models.
Defines immutable/observable state models and detection contracts.
"""

from __future__ import annotations
from enum import Enum
from typing import TypeVar, Generic, Optional, List, Dict, Tuple, Any
from datetime import datetime
from pydantic import BaseModel, Field


class UIState(str, Enum):
    UNKNOWN = "UNKNOWN"
    HOME = "HOME"
    ATTACK_MENU = "ATTACK_MENU"
    MY_ARMY_SCREEN = "MY_ARMY_SCREEN"
    MATCHMAKING = "MATCHMAKING"
    CANDIDATE_BATTLE = "CANDIDATE_BATTLE"
    ACTIVE_BATTLE = "ACTIVE_BATTLE"
    END_BATTLE_DIALOG = "END_BATTLE_DIALOG"
    SURRENDER_DIALOG = "SURRENDER_DIALOG"
    VICTORY_RESULT = "VICTORY_RESULT"
    DEFEAT_RESULT = "DEFEAT_RESULT"
    PICK_REWARD = "PICK_REWARD"
    WALL_SCREEN = "WALL_SCREEN"
    POPUP_MODAL = "POPUP_MODAL"
    PAUSED = "PAUSED"
    ERROR_SAFE_STOP = "ERROR_SAFE_STOP"


class BoundingBox(BaseModel):
    x: int
    y: int
    width: int
    height: int

    @property
    def center(self) -> Tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height


T = TypeVar("T")


class DetectionResult(BaseModel, Generic[T]):
    value: Optional[T] = None
    confidence: float = 0.0
    bbox: Optional[BoundingBox] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    source_frame_id: str = ""
    errors: List[str] = Field(default_factory=list)

    @property
    def is_confident(self) -> bool:
        return self.confidence >= 0.70 and self.value is not None


class CandidateInfo(BaseModel):
    gold: int = 0
    elixir: int = 0
    dark_elixir: int = 0
    confidence: float = 0.0
    is_valid_candidate: bool = False


class BattleInfo(BaseModel):
    is_active: bool = False
    damage_percent: float = 0.0
    time_remaining_seconds: int = 180
    stars: int = 0
    can_end_battle: bool = False
    can_surrender: bool = False
    confidence: float = 0.0


class HomeInfo(BaseModel):
    gold_storage_fill_percent: float = 0.0
    elixir_storage_fill_percent: float = 0.0
    free_builders: int = 0
    total_builders: int = 0
    eligible_walls_found: int = 0
    confidence: float = 0.0


class GameState(BaseModel):
    """Aggregate snapshot of visible game state at a single frame."""
    ui_state: UIState = UIState.UNKNOWN
    state_confidence: float = 0.0
    candidate: CandidateInfo = Field(default_factory=CandidateInfo)
    battle: BattleInfo = Field(default_factory=BattleInfo)
    home: HomeInfo = Field(default_factory=HomeInfo)
    detected_army_slots: List[Dict[str, Any]] = Field(default_factory=list)
    viewport_calibrated: bool = False
    timestamp: datetime = Field(default_factory=datetime.now)
    errors: List[str] = Field(default_factory=list)
