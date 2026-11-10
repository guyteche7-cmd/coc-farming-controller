"""
Army Ledger System (Version 1 — Exact CoC Slot Ribbon Order).
Tracks expected units, runtime detected units, deployed counts, and verifies
deployment completeness across battle stages.

CoC Ribbon Slot Order:
Slot 0: Troops (Valkyries)
Slot 1: Siege Engines (Log Launcher)
Slots 2-5: Heroes (Minion Prince/Champion, Queen, Warden, King)
Slot 6: Spells (Earthquake Spells)
"""

from __future__ import annotations
from enum import Enum
from typing import List, Dict, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field
from src.state.game_state import BoundingBox


class UnitCategory(str, Enum):
    TROOP = "TROOP"
    SIEGE = "SIEGE"
    HERO = "HERO"
    SPELL = "SPELL"
    CLAN_CASTLE = "CLAN_CASTLE"


class UnitStatus(str, Enum):
    EXPECTED = "EXPECTED"
    DEPLOYING = "DEPLOYING"
    DEPLOYED = "DEPLOYED"
    UNDEPLOYED = "UNDEPLOYED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class ArmySlot(BaseModel):
    slot_index: int
    name: str
    category: UnitCategory
    expected_quantity: int = 0
    detected_quantity: int = 0
    deployed_quantity: int = 0
    remaining_quantity: int = 0
    status: UnitStatus = UnitStatus.EXPECTED
    bbox: Optional[BoundingBox] = None
    confidence: float = 0.0
    is_hero_ability_ready: bool = False


class ArmyLedger(BaseModel):
    """Ledger representing expected and real-time state of the attacking army."""
    slots: List[ArmySlot] = Field(default_factory=list)
    last_verified_at: Optional[datetime] = None
    is_fully_deployed: bool = False
    verification_confidence: float = 0.0

    def initialize_baseline(self) -> None:
        """Initializes default baseline army."""
        from src.persistence.config_manager import DeploymentConfig
        self.initialize_from_config(DeploymentConfig())

    def initialize_from_config(self, deployment_config) -> None:
        """
        Initializes baseline slots matching exact Clash of Clans ribbon layout:
        Slot 0: Troops (Valkyrie)
        Slot 1: Siege Engine (Log Launcher)
        Slots 2-5: Heroes (4 Heroes)
        Slot 6: Spells (Earthquake Spell)
        """
        self.slots.clear()

        # Slot 0: Troops
        for troop in deployment_config.army.troops:
            self.slots.append(
                ArmySlot(
                    slot_index=0,
                    name=troop.name,
                    category=UnitCategory.TROOP,
                    expected_quantity=troop.expected_quantity,
                    remaining_quantity=troop.expected_quantity,
                    status=UnitStatus.EXPECTED
                )
            )

        # Slot 1: Siege Engine
        for siege in deployment_config.army.siege:
            self.slots.append(
                ArmySlot(
                    slot_index=1,
                    name=siege.name,
                    category=UnitCategory.SIEGE,
                    expected_quantity=siege.expected_quantity,
                    remaining_quantity=siege.expected_quantity,
                    status=UnitStatus.EXPECTED
                )
            )

        # Slots 2-5: Heroes
        hero_names = ["minion_prince", "archer_queen", "grand_warden", "barbarian_king"]
        for idx, hname in enumerate(hero_names):
            slot_id = 2 + idx
            self.slots.append(
                ArmySlot(
                    slot_index=slot_id,
                    name=hname,
                    category=UnitCategory.HERO,
                    expected_quantity=1,
                    remaining_quantity=1,
                    status=UnitStatus.EXPECTED
                )
            )

        # Slot 6: Spells
        for spell in deployment_config.army.spells:
            self.slots.append(
                ArmySlot(
                    slot_index=6,
                    name=spell.name,
                    category=UnitCategory.SPELL,
                    expected_quantity=spell.expected_quantity,
                    remaining_quantity=spell.expected_quantity,
                    status=UnitStatus.EXPECTED
                )
            )

    def get_slot_by_index(self, slot_index: int) -> Optional[ArmySlot]:
        for slot in self.slots:
            if slot.slot_index == slot_index:
                return slot
        return None

    def get_slot_by_category(self, category: UnitCategory) -> List[ArmySlot]:
        return [slot for slot in self.slots if slot.category == category]

    def record_deployment(self, slot_index: int, count: int = 1) -> None:
        """Records deployed count for a slot and marks DEPLOYED when exhausted."""
        slot = self.get_slot_by_index(slot_index)
        if slot:
            slot.deployed_quantity += count
            slot.remaining_quantity = max(0, slot.expected_quantity - slot.deployed_quantity)
            if slot.remaining_quantity == 0:
                slot.status = UnitStatus.DEPLOYED
            else:
                slot.status = UnitStatus.DEPLOYING

    def update_from_detections(self, detected_slots: List[ArmySlot]) -> None:
        """Updates slot information from computer vision detections."""
        for dslot in detected_slots:
            slot = self.get_slot_by_index(dslot.slot_index)
            if slot:
                slot.detected_quantity = dslot.detected_quantity
                slot.confidence = dslot.confidence
                slot.is_hero_ability_ready = dslot.is_hero_ability_ready
                if dslot.status == UnitStatus.DEPLOYED:
                    slot.status = UnitStatus.DEPLOYED
                    slot.remaining_quantity = 0

        self.is_fully_deployed = all(s.status == UnitStatus.DEPLOYED for s in self.slots if s.category != UnitCategory.SPELL)
        self.last_verified_at = datetime.utcnow()
